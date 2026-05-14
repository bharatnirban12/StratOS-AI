from abc import ABC, abstractmethod
from typing import Dict, Any, List
from shared.contracts.domain import UniversalSimulationState

class BaseSimulationEngine(ABC):
    """
    Abstract interface for all industry-specific economic engines.
    """
    
    @abstractmethod
    def initialize(self, simulation_id: str, assumptions: Dict[str, Any]) -> UniversalSimulationState:
        pass

    @abstractmethod
    def step(self, state: UniversalSimulationState, assumptions: Dict[str, Any]) -> UniversalSimulationState:
        """Advance the simulation by one month."""
        pass

    def run(self, simulation_id: str, assumptions: Dict[str, Any], months: int = 24) -> List[UniversalSimulationState]:
        state = self.initialize(simulation_id, assumptions)
        history = [state]
        
        for m in range(1, months + 1):
            state = self.step(state, assumptions)
            history.append(state)
            
            # Check for termination conditions (bankruptcy, etc.)
            if state.metrics.get("cash", 0) < -1000000:
                break
                
        return history
