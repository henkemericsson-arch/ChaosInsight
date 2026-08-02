class FinalRankingAnalyzer:

    def analyze(self, race):

        print()
        print("=== Slutlig Ranking ===")

        ranking = sorted(
            race.horses,
            key=lambda h: h.get_metric("score"),
            reverse=True
        )

        for i, horse in enumerate(ranking, start=1):

            score = horse.get_metric("score")

            print(
                f"{i}. "
                f"{horse.name:<25}"
                f"{score:>8.2f}"
            )