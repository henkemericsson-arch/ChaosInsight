#
# Den enda ingången Learning Engine behöver (005 avsnitt 18.9):
# after_evaluation(). Kopplar AutoRunner till travens tuner.
#

from learning.trav.tuning_factory import build_tuner_and_log
from learning.tuning.auto_runner import AutoRunner

_runner = AutoRunner(build_tuner_and_log)


def after_evaluation(background=True):
    return _runner.after_evaluation(background=background)


def wait():
    _runner.wait()
