from core.menu import MainMenu

from services.analysis_data_collector import AnalysisDataCollector
from services.score_engine import ScoreEngine

from analysis.analysis_engine import AnalysisEngine
from analysis.register_modules import register_modules


class Controller:

    def __init__(self):

        self.menu = MainMenu()

        self.analysis_collector = AnalysisDataCollector()

        self.analysis_engine = AnalysisEngine()

        self.score_engine = ScoreEngine()

        register_modules(self.analysis_engine)

    def run(self):

        selection = self.menu.show()

        if selection is None:
            return

        analysis_data = self.analysis_collector.collect(
            selection["game"]
        )

        analysis_data = self.analysis_engine.analyze(
            analysis_data
        )

        #
        # OBS: Total Score räknas just nu bara för det
        # första loppet i spelet (analysis_data.horses).
        # Att göra samma sak för alla lopp i systemet
        # (analysis_data.races) är nästa steg, tillsammans
        # med System Generator.
        #

        self.score_engine.calculate(analysis_data)

        print()
        print("=" * 60)
        print("Sammanfattning")
        print("=" * 60)

        print(f"Datum               : {analysis_data.game.date}")
        print(f"Spel                : {analysis_data.game.name}")
        print(f"Bana                : {analysis_data.game.track}")
        print(f"Antal lopp          : {analysis_data.game.races}")
        print(f"Max systemkostnad   : {selection['max_cost']} kr")
        print(f"Risknivå            : {selection['risk']}")
        print(f"Antal spikar        : {selection['spikes']}")
        print(f"Antal lås           : {selection['locks']}")
