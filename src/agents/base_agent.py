from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator

    @abstractmethod
    def execute(self, context: dict) -> dict:
        """Execute the agent's main logic, updating the context."""
        pass
