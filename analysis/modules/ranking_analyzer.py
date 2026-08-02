class RankingAnalyzer:

    def analyze(self, race):

        print()
        print("=== Ranking ===")

        ranking = sorted(
            race.horses,
            key=lambda h: h.get_metric("score"),
            reverse=True
        )

        for place, horse in enumerate(ranking, start=1):

            print(
                f"{place:2}. "
                f"{horse.name:<25} "
                f"{horse.get_metric('score'):>6}"
            )
