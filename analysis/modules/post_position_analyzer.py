from analysis.modules.base_analyzer import BaseAnalyzer


class PostPositionAnalyzer(BaseAnalyzer):

    name = "Spåranalys"

    def analyze(self, race):

        print()
        print("=== Spåranalys ===")

        for horse in race.horses:

            score = 0

            horse.set_metric("post_position_score", score)

            print(
                f"{horse.number:2}. "
                f"{horse.name:<25}"
                f"{score:>6.1f}"
            )