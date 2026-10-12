#
# ParameterProvider - läsvägen för resten av systemet (005 avsnitt 16).
#
# Analysmotorerna frågar providern efter vikter; de känner varken
# databasen eller versionshanteringen. Providern håller en oföränderlig
# ögonblicksbild av den aktiva uppsättningen, så att alla lopp i en analys
# ser samma värden. Saknas tabellen eller går läsningen fel används
# baseline - systemet fungerar då som om parameterlagret inte fanns.
#

from types import MappingProxyType


class ParameterSet:
    #
    # Oföränderlig uppsättning värden med versionsnummer.
    #

    def __init__(self, version, values):
        self.version = version
        self._values = MappingProxyType(dict(values))

    @property
    def values(self):
        return self._values

    def get(self, name):
        return self._values[name]

    def group(self, prefix):
        # {"crowd.odds": 20, ...}.group("crowd") -> {"odds": 20, ...}
        start = prefix + "."
        return {
            key[len(start):]: value
            for key, value in self._values.items()
            if key.startswith(start)
        }


class ParameterProvider:

    def __init__(self, store, baseline):
        self._store = store
        self._baseline = dict(baseline)
        self._snapshot = None

    def current(self):
        if self._snapshot is None:
            self.refresh()
        return self._snapshot

    def refresh(self):
        #
        # Läser om den aktiva uppsättningen. Parametrar som saknas i
        # uppsättningen (t.ex. nya sedan den skapades) fylls på från
        # baseline, så att koden alltid hittar alla namn.
        #
        try:
            self._store.ensure_baseline(self._baseline)
            row = self._store.active()
        except Exception:
            row = None

        if row is None:
            self._snapshot = ParameterSet(0, self._baseline)
            return self._snapshot

        merged = dict(self._baseline)
        merged.update(row["params"])
        self._snapshot = ParameterSet(row["version"], merged)
        return self._snapshot

    def value(self, name):
        return self.current().get(name)

    def group(self, prefix):
        return self.current().group(prefix)

    @property
    def version(self):
        return self.current().version
