class CrowdEngine:

    #
    # Wisdom of the Crowd - Crowd Index (CI)
    #
    # Enligt KAMT-modellen väger CI:s delkomponenter så här
    # (av spelets totala 100%):
    #
    #   Vinnarodds              20 %
    #   Streckprocent           10 %
    #   Oddsutveckling (1h)     10 %
    #   Experttips               5 %
    #   Social konsensus         5 %
    #                           -----
    #   Summa CI                50 %
    #
    # I den här prototypen finns bara Vinnarodds och
    # Streckprocent som riktig data (hämtat från ATG).
    # Oddsutveckling, experttips och social konsensus är
    # inte insamlade än. Crowd Index räknas därför just nu
    # bara på de två komponenter vi faktiskt har, viktade
    # inbördes enligt samma proportion som i KAMT (20:10),
    # och skalas till 0-100.
    #
    # TODO när fler datakällor kopplas in:
    #   - oddsutveckling senaste timmen (finns delvis som
    #     "trend" per häst, men historik över tid saknas)
    #   - experttips
    #   - social konsensus
    #

    ODDS_WEIGHT = 20
    STRECK_WEIGHT = 10

    def analyze(self, race):

        horses = race.horses

        odds_scores = self._score_odds(horses)

        for horse in horses:

            odds_score = odds_scores.get(horse.number, 0)
            streck_score = horse.bet_percentage or 0

            total_weight = self.ODDS_WEIGHT + self.STRECK_WEIGHT

            crowd_index = (
                (odds_score * self.ODDS_WEIGHT)
                + (streck_score * self.STRECK_WEIGHT)
            ) / total_weight

            horse.set_metric("crowd_index", round(crowd_index, 1))

        print()
        print("=== Crowdanalys ===")

        for horse in horses:
            print(
                f"{horse.number:>2}. {horse.name:<20} "
                f"odds:{horse.odds!s:<7} "
                f"streck%:{horse.bet_percentage!s:<6} "
                f"Crowd Index: {horse.get_metric('crowd_index')}"
            )

    @staticmethod
    def _score_odds(horses):

        #
        # Räknar om odds till marknadens implicita
        # vinstsannolikhet per häst (1/odds), och skalar
        # sedan till 0-100 inom loppet.
        #

        implied_probabilities = {}

        for horse in horses:

            if horse.odds and horse.odds > 0:
                implied_probabilities[horse.number] = 1 / horse.odds
            else:
                implied_probabilities[horse.number] = 0

        total = sum(implied_probabilities.values())

        if total == 0:
            return {number: 0 for number in implied_probabilities}

        return {
            number: round((probability / total) * 100, 1)
            for number, probability in implied_probabilities.items()
        }
