#
# AutoRunner - kör övervakning och justering efter en utvärdering
# (005 avsnitt 18.9). Generell: allt travspecifikt kommer via en
# tuner_factory som returnerar (tuner, log).
#
# Garantier: avstängd automatik gör ingenting; ett fel här når aldrig
# anroparen; bara en körning åt gången; körningen sker i en tråd som
# inte är daemon, så den hinner slutföra även om programmet avslutas.
#

import threading


class AutoRunner:

    def __init__(self, tuner_factory):
        self._factory = tuner_factory
        self._lock = threading.Lock()
        self._thread = None

    def after_evaluation(self, background=True):
        # Returnerar True om en körning startades. Anslutningen som
        # kontrollerar "på/av" används bara här; arbetet bygger egna
        # objekt i sin tråd (SQLite-anslutningar delas inte mellan trådar).
        try:
            _, log = self._factory()
            if not log.enabled():
                return False
        except Exception:
            return False
        if not self._lock.acquire(blocking=False):
            return False
        if background:
            self._thread = threading.Thread(target=self._work, daemon=False)
            self._thread.start()
        else:
            self._work()
        return True

    def wait(self):
        if self._thread is not None:
            self._thread.join()

    def _work(self):
        log = None
        try:
            tuner, log = self._factory()
            tuner.monitor()
            tuner.run()
        except Exception as exc:
            try:
                if log is None:
                    _, log = self._factory()
                log.record("error", None, f"{type(exc).__name__}: {exc}")
            except Exception:
                pass
        finally:
            self._lock.release()
