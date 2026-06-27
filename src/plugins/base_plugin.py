from abc import ABC, abstractmethod

class BasePlugin(ABC):
    @abstractmethod
    def fetch_data(self) -> list:
        pass
