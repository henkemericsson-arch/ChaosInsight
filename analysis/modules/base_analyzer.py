from abc import ABC, abstractmethod


class BaseAnalyzer(ABC):

    name = "Base"

    @abstractmethod
    def analyze(self, race):
        """Utför analys av loppet."""
        pass
