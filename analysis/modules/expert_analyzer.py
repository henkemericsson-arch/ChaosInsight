from analysis.modules.base_analyzer import BaseAnalyzer
from config import expert_sources
from expert.scoring import leg_index
from expert.store import latest_per_source
from expert.trav import lexicon
from foundation.database_manager import DatabaseManager

METRIC_ACTIVE = "expert_index"
METRIC_OBSERVE = "expert_index_obs"


class ExpertAnalyzer(BaseAnalyzer):

    #
    # Producerar expertindex per hast ur experttips som redan samlats in
    # och sparats i Knowledge Base (expert_tips). Hamtar ingenting fran
    # natet och sjalvberaknar ingen slutpoang - det ar Data Collectors
    # (expert/collector.py) respektive Score Engines uppgift.
    #
    # Saknas tips for spelet/loppet sats ingen metric (saknad ar inte 0).
    # Metricens namn styrs av EXPERT_INDEX_ACTIVE i config/expert_sources.py:
    # av = "expert_index_obs" (loggas, paverkar inte Total Score),
    # pa = "expert_index" (raknas in av CrowdEngine).
    #

    name = "Expertanalys"

    def __init__(self, db=None):
        self._db = db

    def analyze(self, analysis_data):
        game = getattr(analysis_data, "game", None)
        races = getattr(analysis_data, "races", None) or []
        if game is None or not races:
            return

        db = self._db or DatabaseManager()
        try:
            rows = db.expert_tips_for_game(game.id)
        finally:
            if self._db is None:
                db.close()

        if not rows:
            print(f"[Expertanalys] Inga insamlade experttips for {game.id}.")
            return

        tips = latest_per_source(rows)
        weights = {s["name"]: s.get("weight", 1.0) for s in expert_sources.SOURCES}
        metric = METRIC_ACTIVE if expert_sources.EXPERT_INDEX_ACTIVE else METRIC_OBSERVE

        for leg_number, race in enumerate(analysis_data.races, start=1):
            numbers = [horse.number for horse in race.horses]
            index = leg_index(
                [t for t in tips if t.leg == leg_number],
                numbers, lexicon.SIGNAL_WEIGHTS, lexicon.SUPPORT_CAP, weights,
            )
            for horse in race.horses:
                if horse.number in index:
                    horse.set_metric(metric, index[horse.number])
