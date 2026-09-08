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
    # I den här prototypen finns Vinnarodds, Streckprocent och nu
    # aven en trend-komponent som riktig data, samt Experttips
    # nar ExpertAnalyzer har korts for spelet innan CrowdEngine.
    # Social konsensus ar fortfarande inte insamlad.
    #
    # OBS - viktigt om trend-komponenten: horse.odds_trend heter
    # sa i koden, men extraheras i horse_parser.py genom att leta
    # igenom ALLA hastens pooler och ta "trend"-faltet fran den
    # FORSTA poolen som har ett sadant. I den rådata vi granskat
    # var det V85-poolen (streckprocent-poolen) som hade "trend",
    # inte vinnare-poolen (odds) - fältet mater dartor sannolikt
    # STRECKPROCENTENS rorelse, inte oddsens, trots namnet. Om
    # nagot spel har trend pa en annan pool istallet skulle detta
    # kunna variera. Anvands har som en approximation av KAMT:s
    # "Oddsutveckling"-komponent tills detta ar helt klarlagt.
    #
    # TODO nar fler datakallor kopplas in:
    #   - bekrafta exakt vilken pool horse.odds_trend faktiskt
    #     mater, per speltyp
    #   - social konsensus
    #

    ODDS_WEIGHT = 20
    STRECK_WEIGHT = 10
    TREND_WEIGHT = 10
    EXPERT_WEIGHT = 5

    def analyze(self, race):
        horses = race.horses

        odds_scores = self._score_odds(horses)
        trend_scores = self._score_trend(horses)

        has_expert_data = any(
            "expert_index" in horse.metrics for horse in horses
        )
        has_trend_data = any(
            horse.odds_trend is not None for horse in horses
        )

        total_weight = self.ODDS_WEIGHT + self.STRECK_WEIGHT

        if has_trend_data:
            total_weight += self.TREND_WEIGHT

        if has_expert_data:
            total_weight += self.EXPERT_WEIGHT

        for horse in horses:
            odds_score = odds_scores.get(horse.number, 0)
            streck_score = horse.bet_percentage or 0

            weighted_sum = (
                (odds_score * self.ODDS_WEIGHT)
                + (streck_score * self.STRECK_WEIGHT)
            )

            if has_trend_data:
                trend_score = trend_scores.get(horse.number, 50.0)
                weighted_sum += trend_score * self.TREND_WEIGHT

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
            trend_text = (
                f"trend:{horse.odds_trend!s:<8} "
                if has_trend_data
                else ""
            )
            print(
                f"{horse.number:>2}. {horse.name:<20} "
                f"odds:{horse.odds!s:<7} "
                f"streck%:{horse.bet_percentage!s:<6} "
                f"{trend_text}"
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

    @staticmethod
    def _score_trend(horses):
        #
        # Rankar hastar efter deras trend-varde (se OBS ovan om
        # vad faltet troligen faktiskt mater) - en mer positiv
        # trend (okande stod) ger hogre poang. Skalas relativt
        # inom loppet till 0-100, liknande _score_odds.
        #
        # Hastar utan trend-data (None) far ett neutralt varde
        # (50) individuellt, istallet for att paverka
        # min/max-spannet for de ovriga.
        #
        known_trends = {
            horse.number: horse.odds_trend
            for horse in horses
            if horse.odds_trend is not None
        }

        if not known_trends:
            return {horse.number: 50.0 for horse in horses}

        min_trend = min(known_trends.values())
        max_trend = max(known_trends.values())

        scores = {}
        for horse in horses:
            if horse.number not in known_trends:
                scores[horse.number] = 50.0
                continue

            if max_trend == min_trend:
                scores[horse.number] = 50.0
            else:
                trend = known_trends[horse.number]
                scores[horse.number] = round(
                    ((trend - min_trend) / (max_trend - min_trend)) * 100, 1
                )

        return scores
