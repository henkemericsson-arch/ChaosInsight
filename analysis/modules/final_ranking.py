class FinalRankingAnalyzer:

    def analyze(self, race):

        print()
        print("=== Slutlig Ranking ===")

        ranking = sorted(
            race.horses,
            key=lambda h: h.score,
            reverse=True
        )

        for i, horse in enumerate(ranking, start=1):
            print(f"{i}. {horse.name:20} {horse.score:.2f}")
