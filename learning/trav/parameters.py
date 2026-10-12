#
# Standardprovidern för travflödet: koppar ihop den generella
# ParameterProvider med travens baseline och Knowledge Base.
#

import threading

from foundation.database_manager import get_default_manager
from learning.trav.parameter_schema import BASELINE
from learning.tuning.parameter_provider import ParameterProvider
from learning.tuning.parameter_store import ParameterStore

_lock = threading.Lock()
_provider = None


def get_provider():
    #
    # En provider per process. Databaskopplingen hämtas per tråd
    # (DatabaseManager är trådlokal), därför läser store via en
    # liten wrapper som slår upp managern vid varje anrop.
    #
    global _provider
    with _lock:
        if _provider is None:
            _provider = ParameterProvider(ParameterStore(_ThreadLocalDb()), BASELINE)
        return _provider


class _ThreadLocalDb:

    def __getattr__(self, name):
        return getattr(get_default_manager(), name)
