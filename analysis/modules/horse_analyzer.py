from analysis.modules.base_analyzer import BaseAnalyzer
from services.knowledge_base import KnowledgeBase


class HorseAnalyzer(BaseAnalyzer):

    name = "Hästanalys"

    def __init__(self):
        self.kb = KnowledgeBase()

    def analyze(self, race):

        print()
        print("=== Hästanalys ===")

        for horse in race.horses:

            info = self.kb.horse(horse.name)

            if info:

                score = (
                    info.get("win_percent", 0) * 2 +
                    info.get("top3_percent", 0) * 0.5
                )

                horse.set_metric(
                    "horse_score",
                    round(score, 2)
                )

                print(
                    f"{horse.number:2}. "
                    f"{horse.name:<25}"
                    f"{horse.get_metric('horse_score'):>6}"
                )

            else:

                horse.set_metric(
                    "horse_score",
                    0
                )

                print(
                    f"{horse.number:2}. "
                    f"{horse.name:<25}"
                    " saknas i databasen"
                )