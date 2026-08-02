from analysis.modules.base_analyzer import BaseAnalyzer


class RankingAnalyzer(BaseAnalyzer):

    name = "Ranking"

    def analyze(self, race):

        print()
        print("=== Ranking ===")

        ranking = sorted(
            race.horses,
            key=lambda h: h.get_metric("score"),
            reverse=True
        )

        print(
            f"{'Pl':<3}"
            f"{'Häst':<25}"
            f"{'Speed':>8}"
            f"{'Form':>8}"
            f"{'Stamina':>10}"
            f"{'Risk':>8}"
            f"{'Score':>10}"
        )

        print("-" * 72)

        for place, horse in enumerate(ranking, start=1):

            print(
                f"{place:<3}"
                f"{horse.name:<25}"
                f"{horse.get_metric('speed'):>8.1f}"
                f"{horse.get_metric('form'):>8.1f}"
                f"{horse.get_metric('stamina'):>10.1f}"
                f"{horse.get_metric('risk'):>8.1f}"
                f"{horse.get_metric('score'):>10.2f}"
            )