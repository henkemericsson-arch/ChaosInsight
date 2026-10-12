#
# Bygger travens Tuner (005 avsnitt 18.9). Delas av kommandoraden
# och av auto-kopplingen så att uppsättningen inte dupliceras.
#

from foundation.database_manager import DatabaseManager
from learning.trav.tuning_adapter import TravTuningAdapter, tuning_settings
from learning.tuning.parameter_store import ParameterStore
from learning.tuning.tuner import Tuner
from learning.tuning.tuning_log import TuningLog


def build_tuner(db=None):
    db = db or DatabaseManager()
    adapter = TravTuningAdapter(db.observations_for_analysis)
    return Tuner(ParameterStore(db), TuningLog(db), adapter, tuning_settings()), db


def build_tuner_and_log():
    tuner, db = build_tuner()
    return tuner, TuningLog(db)
