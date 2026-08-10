from analysis.modules.startlist_analyzer import StartlistAnalyzer
from analysis.modules.basic_metrics import BasicMetricsAnalyzer
from analysis.modules.driver_analyzer import DriverAnalyzer
from analysis.modules.horse_analyzer import HorseAnalyzer
from analysis.modules.trainer_analyzer import TrainerAnalyzer
from analysis.modules.track_analyzer import TrackAnalyzer
from analysis.crowd_engine import CrowdEngine
from analysis.chaos_engine import ChaosEngine


def register_modules(engine):

    engine.add_module(StartlistAnalyzer())
    engine.add_module(BasicMetricsAnalyzer())
    engine.add_module(DriverAnalyzer())
    engine.add_module(HorseAnalyzer())
    engine.add_module(TrainerAnalyzer())
    engine.add_module(TrackAnalyzer())
    engine.add_module(CrowdEngine())
    engine.add_module(ChaosEngine())
