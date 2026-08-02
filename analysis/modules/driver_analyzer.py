from services.knowledge_base import KnowledgeBase


class DriverAnalyzer:

    def __init__(self):
        self.kb = KnowledgeBase()

    def analyze(self, race):

        print()
        print("=== Kuskanalys ===")

        for horse in race.horses:

            info = self.kb.driver(horse.driver)

            if info:

                score = (
                    info.get("win_percent", 0) * 2 +
                    info.get("top3_percent", 0) * 0.5
                )

                horse.set_metric("driver_score", round(score, 2))

                print(
                    f"{horse.number:2}. "
                    f"{horse.driver:<25}"
                    f" {horse.get_metric('driver_score'):>6}"
                )

            else:

                horse.set_metric("driver_score", 0)

                print(
                    f"{horse.number:2}. "
                    f"{horse.driver:<25}"
                    " saknas i databasen"
                )
