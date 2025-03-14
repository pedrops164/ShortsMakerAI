from abc import ABC, abstractmethod

class ContentTemplate(ABC):
    @abstractmethod
    def generate_short(self):
        pass