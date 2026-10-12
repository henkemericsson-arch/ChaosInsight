#
# Travadapter för automatisk justering (005 avsnitt 18). Kopplar den
# generella Tuner till travens parametrar, signaler och lopp.
#

from learning.observation_reader import build_races
from learning.trav import settings, weight_features
from learning.trav.parameter_schema import BASELINE


def tuning_settings():
    return {
        "min_races": settings.MIN_RACES_FOR_TUNING,
        "min_new_races": settings.TUNING_MIN_NEW_RACES,
        "damping": settings.TUNING_DAMPING,
        "step_cap": settings.TUNING_STEP_CAP,
        "total_cap": settings.TUNING_TOTAL_CAP,
        "rollback_min_races": settings.ROLLBACK_MIN_RACES,
        "rollback_window": settings.ROLLBACK_WINDOW,
        "ridge": settings.WEIGHT_RIDGE,
    }


class TravTuningAdapter:

    baseline = BASELINE

    # De elva signalernas parametrar; crowd.expert rörs inte (observe-only, 006).
    adjustable = tuple(weight_features.param_names())

    # score.crowd + score.chaos ska vara konstant (1,0).
    sum_groups = (("score.crowd", "score.chaos"),)

    def __init__(self, rows_provider):
        self._rows_provider = rows_provider

    def load_races(self):
        #
        # Bara lopp från aktuell regim (settings.REGIMES, 005 avsnitt 3b):
        # signalernas definition får inte ha ändrats under perioden.
        #
        regimes = getattr(settings, "REGIMES", ()) or ()
        since = regimes[-1][1] if regimes else None

        by_model, _ = build_races(
            self._rows_provider(), {"kamt_v1": settings.MODEL_STRATEGIES["kamt_v1"]},
            excluded_tracks=settings.GALLOP_TRACKS, since=since,
            distance_classes=settings.DISTANCE_CLASSES,
        )
        races, _, _ = weight_features.to_weight_races(by_model["kamt_v1"])
        return races

    @staticmethod
    def effective_weights(params):
        weights = weight_features.effective_weights(params)
        return [weights[name] for name in weight_features.param_names()]

    @staticmethod
    def propose(betas, params):
        return weight_features.to_parameters(
            dict(zip(weight_features.param_names(), betas)), params,
        )
