class ScoreEngine:

    #
    # Kombinerar CrowdIndex och KaosIndex till ett Total
    # Score per häst, enligt KAMT-modellens grundformel:
    #
    #   Total Score = 0,50 x CrowdIndex + 0,50 x KaosIndex
    #
    # ScoreEngine gör ingen egen analys, den bara väger
    # samman metrics som redan satts av CrowdEngine och
    # ChaosEngine.
    #

    CROWD_WEIGHT = 0.50
    CHAOS_WEIGHT = 0.50

    def calculate(self, race):

        for horse in race.horses:

            crowd_index = horse.get_metric("crowd_index")
            chaos_index = horse.get_metric("chaos_index")

            total_score = (
                (crowd_index * self.CROWD_WEIGHT)
                + (chaos_index * self.CHAOS_WEIGHT)
            )

            horse.set_metric("total_score", round(total_score, 1))

        self._print_ranking(race)

    @staticmethod
    def _print_ranking(race):

        ranked_horses = sorted(
            race.horses,
            key=lambda h: h.get_metric("total_score"),
            reverse=True,
        )

        print()
        print("=== Total Score (rankning) ===")

        for placement, horse in enumerate(ranked_horses, start=1):

            print(
                f"{placement:>2}. {horse.number:>2}. {horse.name:<20} "
                f"CI: {horse.get_metric('crowd_index'):<6} "
                f"KI: {horse.get_metric('chaos_index'):<6} "
                f"Total Score: {horse.get_metric('total_score')}"
            )
