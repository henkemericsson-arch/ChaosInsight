from analysis.modules.base_analyzer import BaseAnalyzer


class CrowdEngine(BaseAnalyzer):

    name = "Crowdanalys"

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
    # I den här prototypen finns Vinnarodds och Streckprocent
    # som riktig data (hämtat från ATG), samt Experttips när
    # ExpertAnalyzer har körts för spelet innan CrowdEngine
    # (annars saknas den komponenten helt för det loppet).
    # Oddsutveckling och social konsensus är inte insamlade
    # än. Crowd Index räknas på de komponenter som faktiskt
    # finns tillgängliga för respektive lopp, viktade
    # inbördes enligt samma proportion som i KAMT
    # (20:10:5), och skalas till 0-100.
    #
    # TODO när fler datakällor kopplas in:
    #   - oddsutveckling senaste timmen (finns delvis som
    #     "trend" per häst, men historik över tid saknas)
    #   - social konsensus
    #

    ODDS_WEIGHT = 20
    STRECK_WEIGHT = 10
    EXPERT_WEIGHT = 5

    def analyze(self, race):

        horses = race.horses

        odds_scores = self._score_odds(horses)

        has_expert_data = any(
            "expert_index" in horse.metrics for horse in horses
        )

        total_weight = self.ODDS_WEIGHT + self.STRECK_WEIGHT

        if has_expert_data:
            total_weight += self.EXPERT_WEIGHT

        for horse in horses:

            odds_score = odds_scores.get(horse.number, 0)
            streck_score = horse.bet_percentage or 0

            weighted_sum = (
                (odds_score * self.ODDS_WEIGHT)
                + (streck_score * self.STRECK_WEIGHT)
            )

            if has_expert_data:

                expert_score = horse.get_metric("expert_index")

                weighted_sum += expert_score * self.EXPERT_WEIGHT

            crowd_index = weighted_sum / total_weight

            horse.set_metric("crowd_index", round(crowd_index, 1))

        print()
        print("=== Crowdanalys ===")

        for horse in horses:

            expert_text = (
                f"expert:{horse.get_metric('expert_index')!s:<6} "
                if has_expert_data
                else ""
            )

            print(
                f"{horse.number:>2}. {horse.name:<20} "
                f"odds:{horse.odds!s:<7} "
                f"streck%:{horse.bet_percentage!s:<6} "
                f"{expert_text}"
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
