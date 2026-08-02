from services.data_loader import DataLoader
from services.score_engine import ScoreEngine

from analysis.modules.startlist_analyzer import StartlistAnalyzer
from analysis.modules.basic_metrics import BasicMetricsAnalyzer
from analysis.modules.driver_analyzer import DriverAnalyzer
from analysis.modules.horse_analyzer import HorseAnalyzer
from analysis.modules.trainer_analyzer import TrainerAnalyzer
from analysis.modules.track_analyzer import TrackAnalyzer
from analysis.modules.weather_analyzer import WeatherAnalyzer
from analysis.modules.post_position_analyzer import PostPositionAnalyzer
from analysis.modules.ranking_analyzer import RankingAnalyzer
from analysis.modules.final_ranking import FinalRankingAnalyzer


class RaceAnalysis:

    def __init__(self):

        self.loader = DataLoader()
        self.score_engine = ScoreEngine()

        # Moduler som samlar in fakta
        self.analysis_modules = [
            StartlistAnalyzer(),
            BasicMetricsAnalyzer(),
            DriverAnalyzer(),
            HorseAnalyzer(),
            TrainerAnalyzer(),
            TrackAnalyzer(),
            WeatherAnalyzer(),
            PostPositionAnalyzer(),
        ]

        # Moduler som bara visar resultat
        self.presentation_modules = [
            RankingAnalyzer(),
            FinalRankingAnalyzer(),
        ]

    def analyze(self, race_file):

        race = self.loader.load_race(race_file)

        print()
        print("=" * 60)
        print("Chaos Insight")
        print("=" * 60)

        #
        # FAS 1
        #

        for module in self.analysis_modules:
            module.analyze(race)

        #
        # FAS 2
        #

        self.score_engine.calculate(race)

        #
        # FAS 3
        #

        for module in self.presentation_modules:
            module.analyze(race)