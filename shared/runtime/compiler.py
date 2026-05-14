from typing import List, Dict, Any, Set
from shared.contracts.domain import MultiDomainBlueprint, Capability
from shared.schemas.task import AgentType

class WorkflowCompiler:
    """
    Compiles a high-level Business Blueprint into a validated Execution DAG.
    Handles:
    - Dependency Resolution
    - Cycle Detection
    - Parallel Execution Planning
    """
    
    def __init__(self):
        # Maps capabilities to their logical dependencies
        self.dependency_rules = {
            Capability.FINANCIAL_PROJECTION: [Capability.MARKET_ANALYSIS, Capability.OPERATIONS_PLANNING],
            Capability.GROWTH_STRATEGY: [Capability.MARKET_ANALYSIS],
            Capability.SUPPLY_CHAIN_DESIGN: [Capability.OPERATIONS_PLANNING],
            Capability.RISK_ASSESSMENT: [Capability.FINANCIAL_PROJECTION, Capability.TECHNICAL_ARCHITECTURE]
        }

    def compile(self, blueprint: MultiDomainBlueprint) -> Dict[str, Any]:
        """
        Generates a validated execution plan.
        Returns: { 'layers': [[agent_ids], [agent_ids]], 'metadata': {} }
        """
        capabilities = blueprint.required_capabilities
        
        # 1. Build Adjacency List
        adj: Dict[str, Set[Capability]] = {cap: set() for cap in capabilities}
        for cap in capabilities:
            deps = self.dependency_rules.get(cap, [])
            for dep in deps:
                if dep in capabilities:
                    adj[cap].add(dep)
        
        # 2. Cycle Detection (DFS)
        visited = set()
        path = set()
        
        def has_cycle(u):
            visited.add(u)
            path.add(u)
            for v in adj.get(u, []):
                if v not in visited:
                    if has_cycle(v): return True
                elif v in path:
                    return True
            path.remove(u)
            return False

        for cap in capabilities:
            if cap not in visited:
                if has_cycle(cap):
                    raise ValueError(f"Workflow cycle detected at capability: {cap}")

        # 3. Layered Execution Planning (Topological Sort Variant)
        layers = []
        executed = set()
        remaining = set(capabilities)
        
        while remaining:
            current_layer = []
            for cap in list(remaining):
                # If all dependencies are satisfied
                deps = adj.get(cap, set())
                if all(d in executed for d in deps):
                    current_layer.append(cap)
            
            if not current_layer:
                raise ValueError("Unresolved dependencies in workflow blueprint.")
            
            layers.append(current_layer)
            for cap in current_layer:
                executed.add(cap)
                remaining.remove(cap)
                
        return {
            "execution_layers": layers,
            "total_agents": len(capabilities),
            "is_parallel_safe": True
        }
