from analysis.modules.base_analyzer import BaseAnalyzer
from services.knowledge_base import KnowledgeBase


class TrackAnalyzer(BaseAnalyzer):

    name = "Bananalys"

    def __init__(self):
        self.kb = KnowledgeBase()

    def analyze(self, race):

        print()
        print("=== Bananalys ===")

        info = self.kb.track(race.track)

        if info:

            score = (
                info.get("speed_factor", 0) +
                info.get("passing_factor", 0) +
                info.get("home_stretch_factor", 0)
            )

            score = round(score / 3, 2)

        else:

            score = 0

        print(f"Bana: {race.track}")
        print(f"Banscore: {score}")

        for horse in race.horses:
            horse.set_metric("track_score", score)