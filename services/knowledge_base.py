import json
from pathlib import Path


class KnowledgeBase:

    def __init__(self):
        self.base = Path("knowledge")
        self._cache = {}

    def _filename(self, name):

        return (
            str(name)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("å", "a")
            .replace("ä", "a")
            .replace("ö", "o")
            + ".json"
        )

    def load(self, category, name):

        key = (category, str(name).lower())

        if key in self._cache:
            return self._cache[key]

        path = self.base / category / self._filename(name)

        if not path.exists():
            self._cache[key] = {}
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        except Exception:
            data = {}

        self._cache[key] = data
        return data

    def horse(self, name):
        return self.load("horses", name)

    def driver(self, name):
        return self.load("drivers", name)

    def trainer(self, name):
        return self.load("trainers", name)

    def track(self, name):
        return self.load("tracks", name)

    def weather(self, name):
        return self.load("weather", name)

    def has_horse(self, name):
        return bool(self.horse(name))

    def has_driver(self, name):
        return bool(self.driver(name))

    def has_trainer(self, name):
        return bool(self.trainer(name))

    def clear_cache(self):
        self._cache.clear()