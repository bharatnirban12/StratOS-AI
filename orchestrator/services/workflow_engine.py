from pydantic import ValidationError
from aiokafka.consumer import subscription_state
from shared.runtime.governance import RuntimeGovernance as governance
import time
import uuid
from typing import List, Dict, Any, Optional
from loguru import logger
from pydantic import  ValidationError

from shared.contracts.domain import MultiDomainBlueprint
from shared.schemas.event import Event, EventType
from shared.storage.cache import cache_result, get_cached_result
from shared.storage.db import save_simulation_result
from shared.runtime.compiler import WorkflowCompiler



CAPABILITY_TO_AGENT = {
    "market_analysis": "market",
    "financial_projection": "finance",
    "technical_architecture": "ml",
    "growth_strategy": "product",
    "operations_planning": "execution",
    "risk_assessment": "evaluator",
    "supply_chain_design": "execution",
    "strategic_vision": "ceo",
    "business_blueprinting": "architect"
}


def normalize_agent_result(agent_name: str, result: dict):

    if not isinstance(result, dict):
        result = {"raw_output": str(result)}

    structured = result.get("structured_output")

    # Safe fallback
    if structured is None:
        if isinstance(result, dict):
            structured = result
        else:
            raise ValueError(
                f"Missing structured_output from {agent_name}"
            )

    # Final defensive guarantee
    if not isinstance(structured, dict):
        structured = {
            "raw_output": str(structured)
        }

    capability_map = {
        "architect": "business_blueprinting",
        "market": "market_analysis",
        "ml": "technical_architecture",
        "finance": "financial_projection",
        "product": "growth_strategy",
        "execution": "operations_planning",
        "evaluator": "risk_assessment",
        "ceo": "strategic_vision"
    }

    raw_cap = result.get("capability")
    
    # Priority normalization logic:
    # 1. If raw_cap is a known capability, trust it.
    # 2. If raw_cap is in the local map (alias), use the mapped value.
    # 3. Fallback to the agent's default capability.
    # 4. Fallback to raw_cap or agent_name.
    
    if raw_cap in CAPABILITY_TO_AGENT:
        normalized_capability = raw_cap
    elif raw_cap in capability_map:
        normalized_capability = capability_map[raw_cap]
    else:
        # Check if agent has a default mapping
        default_cap = capability_map.get(agent_name)
        if default_cap:
            normalized_capability = default_cap
        else:
            normalized_capability = raw_cap or agent_name

    return {
        "agent_id": result.get("agent_id", agent_name),
        "capability": normalized_capability,
        "narrative": result.get("narrative", ""),
        "structured_output": structured
    }



class WorkflowState:
    def __init__(self, simulation_id: str, goal: str, constraints: Dict[str, Any]):
        self.simulation_id = simulation_id
        self.goal = goal
        self.constraints = constraints
        self.blueprint: Optional[MultiDomainBlueprint] = None
        self.execution_plan = {}
        self.completed_tasks = set()
        self.active_tasks = set()
        self.trace_id = None
        self.task_timestamps = {}
        self.results = {}



class DynamicWorkflowEngine:
    def __init__(self, publisher):
        self.publisher = publisher
        self.states: Dict[str, WorkflowState] = {}
        self.processed_events = set()
        self.failed_tasks = set()

    async def handle_event(self, event_type: str, data: Dict[str, Any]):
        simulation_id = data.get("simulation_id")
        if not simulation_id:
            return

        payload = data.get("full_payload", {})

        if event_type == EventType.TASK_CREATED.value:
            logger.info(f"🆕 Initializing workflow for simulation {simulation_id}")
            
            goal = payload.get("goal", "Startup Idea")
            constraints = payload.get("constraints", {})
            
            state = WorkflowState(simulation_id, goal, constraints)
            self.states[simulation_id] = state
            
            # Initial task is always the architect
            governance.validate_execution(
                state,
                "architect"
            )

            await self._dispatch_next_tasks(simulation_id, ["architect"], state)

        elif event_type == EventType.AGENT_FAILED.value:
            agent = data.get("agent")
            payload = data.get("full_payload", {})
            error_msg = payload.get("error", "Unknown error")
            
            state = self.states.get(simulation_id)
            if state:
                logger.error(f"❌ Agent {agent} failed with error: {error_msg}. Tracking failure.")
                capability = payload.get("capability", agent)
                
                # We do NOT remove from active_tasks right away to avoid an infinite loop of immediate redispatch 
                # without proper backoff, OR we could remove it and let a dead-letter queue handle it.
                # For resilience, let's remove it and let the workflow timeout logic or circuit breakers handle it,
                # but to avoid immediate rapid-fire loops, we just mark it failed.
                
                # To prevent total deadlock, if it's the architect, we must abort.
                if capability == "business_blueprinting" or agent == "architect":
                    logger.error(f"Critical failure in Architect. Aborting simulation {simulation_id}.")
                    state.active_tasks.discard(agent)
                    state.active_tasks.discard("business_blueprinting")
                    self.failed_tasks.add(f"{simulation_id}:{agent}")
                else:
                    # Let the timeout logic in _get_next_tasks handle it, or we can just drop it from active tasks 
                    # and let the DAG retry. But to prevent loop, let's just keep it in failed_tasks.
                    self.failed_tasks.add(f"{simulation_id}:{capability}")
                    state.active_tasks.discard(capability)
                    state.active_tasks.discard(agent)
                    
                # Attempt to get next tasks if possible (e.g. if we want to continue other parallel branches)
                next_tasks = self._get_next_tasks(state)
                if next_tasks:
                    await self._dispatch_next_tasks(simulation_id, next_tasks, state)

        elif event_type == EventType.AGENT_COMPLETED.value:

            agent = data.get("agent")

            raw_result = data.get("results", {}).get(agent) or data.get("full_payload", {})
            agent_result = normalize_agent_result(agent, raw_result)
            capability = agent_result.get("capability", agent) if agent_result else agent

            # Unique event identity using capability so agents can run multiple times
            event_key = f"{simulation_id}:{agent}:{capability}"

            # Skip duplicate Kafka deliveries
            if event_key in self.processed_events:

                logger.warning(
                    f"Duplicate event ignored: {event_key}"
                )

                return

            # Mark processed
            self.processed_events.add(event_key)
            
            
            state = self.states.get(simulation_id)
            if not state:
                logger.warning(f"⚠️ State lost for {simulation_id}. Rehydrating...")
                cached = get_cached_result(simulation_id) or {}
                state = WorkflowState(simulation_id, cached.get("goal", "Recovered"), cached.get("constraints", {}))
                state.results = cached.get("results", {})

                cached_completed = cached.get("completed_tasks", [])

                if cached_completed:
                    state.completed_tasks = set(cached_completed)
                else:
                    # Fallback reconstruction
                    state.completed_tasks = set(state.results.keys())

                cached_active = cached.get("active_tasks", [])
                state.active_tasks = set(cached_active)

                state.execution_plan = cached.get("execution_plan", {})
                
                self.states[simulation_id] = state

                # Restore blueprint
                blueprint_data = cached.get("blueprint")

                if blueprint_data:
                    try:
                        state.blueprint = MultiDomainBlueprint(**blueprint_data)
                    except Exception as e:
                        logger.error(f"Failed to restore blueprint: {e}")

                # Restore trace_id
                state.trace_id = cached.get("trace_id")

            logger.info(f"✅ Agent {agent} completed. Updating results...")
            
            raw_result = data.get("results", {}).get(agent) or data.get("full_payload")

            agent_result = normalize_agent_result(agent, raw_result)
            
            # Update results
            if agent_result:
                capability = agent_result.get(
                    "capability",
                    agent
                )
                storage_key = f"{agent}:{capability}"

                state.results[storage_key] = agent_result
                state.completed_tasks.add(capability)

               # Remove capability key
                if storage_key in state.active_tasks:
                    state.active_tasks.remove(storage_key)

                # Remove raw capability key
                if capability in state.active_tasks:
                    state.active_tasks.remove(capability)

                # Remove runtime agent key fallback
                if agent in state.active_tasks:
                    state.active_tasks.remove(agent)
                    
                # Fix timeout leak: Remove from timestamps so it doesn't falsely trigger a timeout 5 minutes later
                state.task_timestamps.pop(capability, None)
                state.task_timestamps.pop(storage_key, None)
                state.task_timestamps.pop(agent, None)
                
                current_data = {
                    "status": "IN_PROGRESS",
                    "results": state.results,
                    "active_tasks": list(state.active_tasks),
                    "completed_tasks": list(state.completed_tasks),
                    "goal": state.goal,
                    "constraints": state.constraints,
                    "execution_plan": state.execution_plan,
                    "last_updated": time.time()
                }

                cache_result(simulation_id, current_data)

            # Architect completion unlocks the blueprint and execution plan
            if agent == "architect":
                blueprint_data = agent_result.get("structured_output") if agent_result else None
                if not blueprint_data and agent_result:
                    # Fallback if structured_output is missing
                    blueprint_data = agent_result
                    
                if blueprint_data:
                    try:
                        # 1. Clean blueprint data (exclude execution_plan as it's generated by the compiler)
                        valid_fields = MultiDomainBlueprint.model_json_schema().get("properties", {}).keys()
                        filtered_data = {k: v for k, v in blueprint_data.items() if k in valid_fields and k != "execution_plan"}
                        
                        # 2. Initialize Blueprint
                        try:
                            state.blueprint = MultiDomainBlueprint(**filtered_data)

                        except ValidationError as e:
                            logger.error(f"Blueprint validation failed: {e}")
                            return
                        
                        # 3. Compile the Execution Plan (The source of truth for layers)
                        compiler = WorkflowCompiler()
                        state.execution_plan = compiler.compile(state.blueprint)
                        
                        logger.info(f"📍 Execution plan compiled: {len(state.execution_plan.get('execution_layers', []))} layers generated")
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to parse/compile blueprint: {e}")

            next_tasks = self._get_next_tasks(state)
            
            if next_tasks:

                for capability in next_tasks:
                
                    governance.validate_execution(
                        state,
                        capability
                    )
                    
                await self._dispatch_next_tasks(simulation_id, next_tasks, state)
            
            elif (not next_tasks and not state.active_tasks and state.execution_plan):
                logger.info(f"🏁 Simulation {simulation_id} complete! Filing final report.")
                
                final_data = {
                    "results": state.results,
                    "status": "COMPLETED",
                    "goal": state.goal,
                    "constraints": state.constraints,

                    "active_tasks": list(state.active_tasks),
                    "completed_tasks": list(state.completed_tasks),

                    "execution_plan": state.execution_plan,

                    "blueprint": (
                        state.blueprint.model_dump()
                        if state.blueprint else {}
                    ),
                    
                    "last_updated": time.time()
                 }
                
                save_simulation_result(simulation_id, final_data)
                cache_result(simulation_id, final_data) # Sync cache with final state
                
                if simulation_id in self.states:
                    del self.states[simulation_id]

  
    
    def _get_next_tasks(self, state: WorkflowState) -> List[str]:
        
        TASK_TIMEOUT_SECONDS = 300

        expired_tasks = []

        for capability, ts in state.task_timestamps.items():
            if time.time() - ts > TASK_TIMEOUT_SECONDS:
                expired_tasks.append(capability)

        for capability in expired_tasks:
            logger.error(f"Task timeout: {capability}")

            state.active_tasks.discard(capability)
            state.task_timestamps.pop(capability, None)  
        
        # If architect isn't done, nothing else can start
        if "business_blueprinting" not in state.completed_tasks:
            return []

        plan = state.execution_plan
        layers = plan.get("execution_layers", [])
        
        if not layers:
            logger.warning(
                "No execution layers found. "
                "Skipping evaluator dispatch."
            )
            return []

        # Find the first layer that isn't fully completed
        for layer in layers:
            # Use capability names for checking completion
            pending_capabilities = []
            active_caps = []
            
            for cap in layer:
                cap_name = cap.value if hasattr(cap, 'value') else str(cap)
                if cap_name not in state.completed_tasks and cap_name not in state.active_tasks:
                    pending_capabilities.append(cap_name)
                if cap_name in state.active_tasks:
                    active_caps.append(cap_name)
            
            if pending_capabilities:
                return pending_capabilities
            
            if active_caps:
                # Still waiting on this layer
                return []
        
        return []

    async def _dispatch_next_tasks(self, simulation_id: str, capabilities: List[str], state: WorkflowState):
        for capability in capabilities:

            if capability in state.active_tasks:

                logger.warning(
                    f"Skipping duplicate task dispatch: {capability}"
                )

                continue

            if capability in state.completed_tasks:

                logger.warning(
                    f"Skipping completed task: {capability}"
                )

                continue

            # Map capability to agent
            agent_id = CAPABILITY_TO_AGENT.get(capability)

            if not agent_id:

                if state.blueprint:

                    agent_id = (
                        state.blueprint
                        .map_capability_to_agent(capability)
                    )

                else:

                    agent_id = capability

            logger.info(
                f"🚀 Dispatching Capability: "
                f"{capability} to Agent: {agent_id}"
            )

            state.active_tasks.add(capability)

            state.task_timestamps[
                capability
            ] = time.time()

            architect_data = (
                state.results.get(
                    "business_blueprinting"
                )
                or state.results.get("architect")
                or {}
            )

            payload = {
                "agent": agent_id,
                "capability": capability,
                "simulation_id": simulation_id,
                "goal": state.goal,
                "constraints": state.constraints,
                "input": state.results,
                "personal_api_key":
                    architect_data.get(
                        "personal_api_key"
                    )
            }

            event = Event(
                event_type=EventType.TASK_ASSIGNED,
                simulation_id=simulation_id,
                source="orchestrator",
                payload=payload,
                trace_id=(
                    architect_data.get("trace_id")
                    or simulation_id
                )
            )

            await self.publisher.publish(
                "tasks",
                event
            )