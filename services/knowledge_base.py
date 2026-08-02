import json
from pathlib import Path


class KnowledgeBase:

    def __init__(self):
        self.base = Path("knowledge")

    def _filename(self, name):

        return (
            name.lower()
            .replace(" ", "_")
            .replace("å", "a")
            .replace("ä", "a")
            .replace("ö", "o")
            + ".json"
        )

    def load(self, category, name):

        path = self.base / category / self._filename(name)

        if not path.exists():
            return {}

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

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
