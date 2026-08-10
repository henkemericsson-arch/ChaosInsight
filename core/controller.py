from core.menu import MainMenu

from services.analysis_data_collector import AnalysisDataCollector
from services.score_engine import ScoreEngine
from services.system_generator import SystemGenerator

from analysis.analysis_engine import AnalysisEngine
from analysis.register_modules import register_modules
from analysis.crowd_engine import CrowdEngine
from analysis.chaos_engine import ChaosEngine


class Controller:

    def __init__(self):

        self.menu = MainMenu()

        self.analysis_collector = AnalysisDataCollector()

        self.analysis_engine = AnalysisEngine()

        self.crowd_engine = CrowdEngine()
        self.chaos_engine = ChaosEngine()
        self.score_engine = ScoreEngine()

        self.system_generator = SystemGenerator()

        register_modules(self.analysis_engine)

    def run(self):

        selection = self.menu.show()

        if selection is None:
            return

        analysis_data = self.analysis_collector.collect(
            selection["game"]
        )

        #
        # Kör den fulla modulkedjan (kusk/häst/tränar/bana
        # m.fl., inklusive KnowledgeBase-uppslag) på det
        # första loppet, för utskrift/felsökning.
        #

        analysis_data = self.analysis_engine.analyze(
            analysis_data
        )

        #
        # Kör Crowd-, Kaos- och Score-analys på ALLA lopp
        # i systemet, eftersom System Generator behöver
        # rankning för varje delopp.
        #

        for race in analysis_data.races:

            self.crowd_engine.analyze(race)
            self.chaos_engine.analyze(race)
            self.score_engine.calculate(race)

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

        self.system_generator.generate(
            races=analysis_data.races,
            max_cost=selection["max_cost"],
            risk=selection["risk"],
            spikes=selection["spikes"],
            locks=selection["locks"],
        )
