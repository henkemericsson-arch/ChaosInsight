from analysis.modules.base_analyzer import BaseAnalyzer
from services.knowledge_base import KnowledgeBase


class WeatherAnalyzer(BaseAnalyzer):

    name = "Väderanalys"

    def __init__(self):
        self.kb = KnowledgeBase()

    def analyze(self, race):

        print()
        print("=== Väderanalys ===")

        info = self.kb.weather(race.track)

        if info:

            print(f"Väder: {info.get('weather', 'okänt')}")
            print(f"Temperatur: {info.get('temperature', '-')}")
            print(f"Vind: {info.get('wind', '-')}")

        else:

            print("Ingen väderdata i databasen.")