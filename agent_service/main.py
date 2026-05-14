from shared.logger import get_logger
from shared.metrics import track_time

import asyncio
import json
from collections import defaultdict
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from dotenv import load_dotenv

from shared.schemas.event import Event, EventType
from shared.retry import retry_async
from shared.circuit import CircuitBreaker

from agent_service.agents.ceo_agent import CEOAgent
from agent_service.agents.market_agent import MarketAgent
from agent_service.agents.finance_agent import FinanceAgent
from agent_service.agents.product_agent import ProductAgent
from agent_service.agents.ml_agent import MLAgent
from agent_service.agents.execution_agent import ExecutionAgent
from agent_service.agents.evaluator_agent import EvaluatorAgent
from agent_service.agents.architect_agent import BusinessArchitectAgent
from agent_service.runtime.executor import UniversalAgentRuntime
from shared.prometheus import agent_latency, agent_failures


load_dotenv()

KAFKA_TOPIC = "tasks"
DLQ_TOPIC = "tasks_dlq"
KAFKA_BOOTSTRAP = "kafka:9092"


AGENT_FACTORIES = {
    "architect": BusinessArchitectAgent,
    "ceo": CEOAgent,
    "market": MarketAgent,
    "product": ProductAgent,
    "ml": MLAgent,
    "finance": FinanceAgent,
    "execution": ExecutionAgent,
    "evaluator": EvaluatorAgent,
}

async def send_to_dlq(producer, event, error_message):
    dlq_payload = {
        "original_event": event.to_dict(),
        "error": error_message
    }

    await producer.send_and_wait(
        DLQ_TOPIC,
        json.dumps(dlq_payload).encode()
    )
    


async def start_agent_worker():
    logger = get_logger("agent-service")
    
    from agent_service.metrics_server import start_metrics_server
    start_metrics_server()

    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="agent-group",

        session_timeout_ms=60000,

        heartbeat_interval_ms=15000,

        max_poll_interval_ms=300000
    )

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP
    )

    async def wait_for_kafka(consumer, retries=10):
        for i in range(retries):
            try:
                await consumer.start()
                logger.info("Connected to Kafka")
                return
            except Exception:
                logger.warning(f"Kafka not ready, retry {i+1}...")
                await asyncio.sleep(5)
        raise Exception("Kafka not available")

    await wait_for_kafka(consumer)
    await producer.start()
    breakers = defaultdict(CircuitBreaker)

    try:
        async for msg in consumer:
            event = Event.from_dict(json.loads(msg.value.decode()))
            if event is None:

                logger.error(
                    "Failed to parse Kafka event"
                )

                continue
            
            if event.event_type != EventType.TASK_ASSIGNED:
                continue

            logger.info(
                f"Received event: {event.event_type}",
                extra={
                    "service": "agent-service",
                    "simulation_id": event.simulation_id,
                    "trace_id": event.trace_id,
                    "parent_id": event.parent_id
                }
            )

            # ONLY process tasks assigned to agents
            if event.event_type != EventType.TASK_ASSIGNED:
                continue

            payload = event.payload
            payload["simulation_id"] = event.simulation_id
            agent_name = payload.get("agent")

            if not agent_name:
                logger.error("Event missing agent target", extra={"simulation_id": event.simulation_id})
                continue

            # Get agent instance (Static or Dynamic)
            if agent_name in AGENT_FACTORIES:
                agent = AGENT_FACTORIES[agent_name]()
            else:
                logger.info(f"Hydrating universal runtime for specialist: {agent_name}")
                try:
                    agent = UniversalAgentRuntime(agent_name)
                except Exception as e:
                    logger.error(f"Failed to hydrate specialist {agent_name}: {e}")
                    continue

            breaker = breakers[agent_name]
            if breaker.is_open():
                logger.warning(
                    "Circuit open, skipping agent",
                    extra={
                        "service": "agent-service",
                        "simulation_id": event.simulation_id,
                        "agent": agent_name
                    }
                )
                new_event = Event(
                    event_type=EventType.AGENT_FAILED,
                    simulation_id=event.simulation_id,
                    trace_id=event.trace_id,
                    parent_id=event.id,
                    source="agent-service",
                    payload={
                        "agent": agent_name,
                        "error": "CircuitBreaker is OPEN"
                    }
                )
                await producer.send_and_wait(
                    KAFKA_TOPIC,
                    json.dumps(new_event.to_dict()).encode()
                )
                continue

            with track_time() as timer:
                logger.info(
                    f"Running agent: {agent_name}",
                    extra={
                        "service": "agent-service",
                        "simulation_id": event.simulation_id,
                        "trace_id": event.trace_id,
                        "parent_id": event.parent_id,
                        "agent": agent_name
                    }
                )

                try:
                    async def run():
                        return await agent.execute(payload)

                    result = await retry_async(run)
                    breaker.record_success()

                    duration = timer()
                    agent_latency.labels(agent_name=agent_name).observe(duration)
                    
                    logger.info(
                        f"Agent completed: {agent_name}",
                        extra={
                            "service": "agent-service",
                            "simulation_id": event.simulation_id,
                            "agent": agent_name,
                            "duration_sec": duration
                        }
                    )

                    new_event = Event(
                        event_type=EventType.AGENT_COMPLETED,
                        simulation_id=event.simulation_id,
                        trace_id=event.trace_id,
                        parent_id=event.id,
                        source="agent-service",
                        payload={
                            **result,

                            "agent": agent_name,

                            "runtime_agent": agent_name,

                            "capability": (
                                result.get("capability")
                                or payload.get("capability")
                            ),

                            "persona": payload.get("persona")
                        }
                    )


                except Exception as e:
                    breaker.record_failure()
                    await send_to_dlq(
                        producer,
                        event,
                        str(e)
                    )
                    
                    agent_failures.labels(agent_name=agent_name).inc()
                    
                    logger.error(
                        f"Agent {agent_name} failed: {str(e)}",
                        extra={
                            "service": "agent-service",
                            "simulation_id": event.simulation_id,
                            "agent": agent_name,
                            "error": str(e)
                        }
                    )
                    
                    new_event = Event(
                        event_type=EventType.AGENT_FAILED,
                        simulation_id=event.simulation_id,
                        trace_id=event.trace_id,
                        parent_id=event.id,
                        source="agent-service",
                        payload={
                            "agent": agent_name,
                            "error": str(e)
                        }
                    )

            await producer.send_and_wait(
                KAFKA_TOPIC,
                new_event.to_json().encode()
            )
            
            await consumer.commit()

    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(start_agent_worker())