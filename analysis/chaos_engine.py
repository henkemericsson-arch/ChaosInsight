import math

from analysis.modules.base_analyzer import BaseAnalyzer
from services.historical_stats import get_default_provider


class ChaosEngine(BaseAnalyzer):
    name = "Kaosanalys"
    #
    # KaosIndex (KI) - enligt KAMT-modellen
    #
    # Delkomponenter (av spelets totala 100%):
    #
    #   Startspår                8 %
    #   Kuskform                 8 %
    #   Hästens dagsform        10 %
    #   Stallform                5 %
    #   Distansstatistik         5 %
    #   Bana/underlag            4 %
    #   Galopprisk                5 %
    #   Tempoanalys               5 %
    #                           -----
    #   Summa KI                 50 %
    #
    # De fyra sista komponenterna harleds ur den insamlade
    # historiken (data/history/) via HistoricalStatsProvider,
    # baserat pa dagens distans och bantyp.
    #
    # Nar en komponent saknar tillracklig historik for en
    # specifik hast anvands ett neutralt varde (NEUTRAL_SCORE)
    # istallet for att gissa - varken straff eller bonus for
    # okand bakgrund. Detta galler konsekvent for samtliga atta
    # komponenter, inklusive de fyra ursprungliga (som tidigare
    # föll tillbaka pa 0 vid saknad data, vilket i praktiken
    # straffade okand bakgrund hart). Antalet komponenter dar
    # historik faktiskt fanns sparas separat per hast som
    # "data_coverage" (t.ex. "6/8"), sa att osakerheten syns
    # utan att paverka sjalva poangen.
    #

    START_POSITION_WEIGHT = 8
    DRIVER_FORM_WEIGHT = 8
    HORSE_FORM_WEIGHT = 10
    TRAINER_FORM_WEIGHT = 5
    DISTANCE_WEIGHT = 5
    TRACK_CONDITION_WEIGHT = 4
    GALLOP_RISK_WEIGHT = 5
    TEMPO_WEIGHT = 5

    NEUTRAL_SCORE = 50
    DISTANCE_MARGIN = 100

    def __init__(self, historical_stats=None):
        self.historical_stats = historical_stats or get_default_provider()

    def analyze(self, race):
        horses = race.horses

        position_scores = self._score_start_positions(horses)

        total_weight = (
            self.START_POSITION_WEIGHT
            + self.DRIVER_FORM_WEIGHT
            + self.HORSE_FORM_WEIGHT
            + self.TRAINER_FORM_WEIGHT
            + self.DISTANCE_WEIGHT
            + self.TRACK_CONDITION_WEIGHT
            + self.GALLOP_RISK_WEIGHT
            + self.TEMPO_WEIGHT
        )

        #
        # Tempo maste normaliseras (min-max) inom just det har
        # loppets falt, eftersom det ar en tidsdifferens i
        # sekunder - inte redan en 0-100-skala som ovriga
        # komponenter.
        #
        raw_tempo = {
            horse.number: self.historical_stats.tempo_differential(
                horse.name, race.distance, self.DISTANCE_MARGIN
            )
            for horse in horses
        }
        tempo_scores = self._normalize_tempo(raw_tempo)

        track_condition = getattr(race, "track_condition", None)

        for horse in horses:
            missing = 0

            def score_or_neutral(value):
                nonlocal missing
                if value is None:
                    missing += 1
                    return self.NEUTRAL_SCORE
                return value

            position_score = position_scores.get(horse.number, 0)
            driver_score = score_or_neutral(horse.driver_win_pct)
            horse_score = score_or_neutral(horse.horse_win_pct)
            trainer_score = score_or_neutral(horse.trainer_win_pct)

            distance_score = score_or_neutral(
                self.historical_stats.distance_score(
                    horse.name, race.distance, self.DISTANCE_MARGIN
                )
            )
            track_condition_score = score_or_neutral(
                self.historical_stats.track_condition_score(
                    horse.name, track_condition
                )
            )
            gallop_score = score_or_neutral(
                self.historical_stats.gallop_risk_score(horse.name)
            )
            tempo_score = score_or_neutral(tempo_scores.get(horse.number))

            chaos_index = (
                (position_score * self.START_POSITION_WEIGHT)
                + (driver_score * self.DRIVER_FORM_WEIGHT)
                + (horse_score * self.HORSE_FORM_WEIGHT)
                + (trainer_score * self.TRAINER_FORM_WEIGHT)
                + (distance_score * self.DISTANCE_WEIGHT)
                + (track_condition_score * self.TRACK_CONDITION_WEIGHT)
                + (gallop_score * self.GALLOP_RISK_WEIGHT)
                + (tempo_score * self.TEMPO_WEIGHT)
            ) / total_weight

            horse.set_metric("chaos_index", round(chaos_index, 1))
            horse.set_metric("data_coverage", f"{8 - missing}/8")

        kaosvarde = self._calculate_kaosvarde(horses)
        race.kaosvarde = kaosvarde

        print()
        print("=== Kaosanalys ===")
        for horse in horses:
            print(
                f"{horse.number:>2}. {horse.name:<20} "
                f"spår:{horse.start_position!s:<4} "
                f"Kaos Index: {horse.get_metric('chaos_index'):<6} "
                f"(datatäckning: {horse.get_metric('data_coverage')})"
            )

        print()
        print(f"Kaosvärde för loppet: {kaosvarde} ({self._kaosvarde_label(kaosvarde)})")

    @staticmethod
    def _normalize_tempo(raw_tempo):
        #
        # Min-max-normaliserar tempo-differenser (sekunder) inom
        # loppets falt till en 0-100-skala. Lagre (snabbare)
        # differens ger hogre poang. Hastar utan berakningsbar
        # differens far None (hanteras som neutralt varde av
        # anroparen via score_or_neutral).
        #
        values = [v for v in raw_tempo.values() if v is not None]

        if len(values) < 2:
            return {number: None for number in raw_tempo}

        min_value = min(values)
        max_value = max(values)

        if max_value == min_value:
            return {
                number: (100 if v is not None else None)
                for number, v in raw_tempo.items()
            }

        scores = {}
        for number, v in raw_tempo.items():
            if v is None:
                scores[number] = None
                continue

            #
            # Inverterat: lagst differens (snabbast) -> 100,
            # hogst differens (langsammast) -> 0.
            #
            scaled = 100 * (max_value - v) / (max_value - min_value)
            scores[number] = round(scaled, 1)

        return scores

    @staticmethod
    def _score_start_positions(horses):
        #
        # Rangordnar hästarna efter startspår (lägre spår
        # = bättre utgångsläge i de flesta travlopp) och
        # skalar om till 0-100 inom loppet.
        #
        horses_with_position = [
            h for h in horses if h.start_position is not None
        ]

        if not horses_with_position:
            return {h.number: 0 for h in horses}

        sorted_horses = sorted(
            horses_with_position, key=lambda h: h.start_position
        )

        count = len(sorted_horses)
        scores = {}

        for rank, horse in enumerate(sorted_horses):
            if count > 1:
                score = 100 * (count - rank) / count
            else:
                score = 100

            scores[horse.number] = round(score, 1)

        for horse in horses:
            if horse.number not in scores:
                scores[horse.number] = 0

        return scores

    @staticmethod
    def _calculate_kaosvarde(horses):
        #
        # Kaosvärdet för loppet (skiljer sig från hästarnas
        # individuella KaosIndex) mäter hur oenig/spridd
        # crowdens bedömning är, baserat på Shannon-entropi
        # över streckprocenten. En crowd som är helt enig
        # (all insats på en häst) ger lågt kaosvärde. En
        # crowd som är helt splittrad (jämnt fördelat över
        # alla hästar) ger högt kaosvärde.
        #
        percentages = [
            (h.bet_percentage / 100)
            for h in horses
            if h.bet_percentage
        ]

        if not percentages or len(horses) < 2:
            return 0

        entropy = -sum(
            p * math.log(p) for p in percentages if p > 0
        )

        max_entropy = math.log(len(horses))
        if max_entropy == 0:
            return 0

        kaosvarde = round((entropy / max_entropy) * 100, 1)

        return kaosvarde

    @staticmethod
    def _kaosvarde_label(kaosvarde):
        if kaosvarde <= 30:
            return "Stabilt lopp"
        elif kaosvarde <= 60:
            return "Normalt"
        else:
            return "Kaoslopp"
