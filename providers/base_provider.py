from abc import ABC, abstractmethod


class BaseProvider(ABC):

    #
    # En Provider samlar bara in fakta fran en extern kalla
    # (Bibelns "Data Collector"-lager). Den analyserar aldrig,
    # rankar aldrig och rakna aldrig ut poang - det gor
    # analysmoduler (t.ex. en framtida ExpertAnalyzer) med
    # datan som providern samlat in.
    #

    name = "Base"

    @abstractmethod
    def collect(self, *args, **kwargs):
        """Samlar in radata fran kallan."""
        pass
