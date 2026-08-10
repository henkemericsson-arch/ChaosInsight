import math

from analysis.modules.base_analyzer import BaseAnalyzer


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
    # I den här prototypen finns bara startspår som riktig
    # data. Kuskform, hästform, stallform, distansstatistik,
    # bana/underlag, galopprisk och tempoanalys kräver mer
    # historik än vad som samlas in än. Häst-KaosIndex räknas
    # därför just nu bara på startspår.
    #
    # TODO när fler datakällor kopplas in:
    #   - kuskform (kuskens statistik finns delvis i rådata
    #     från ATG men parsas inte än)
    #   - hästens dagsform / stallform
    #   - distansstatistik
    #   - bana/underlag
    #   - galopprisk
    #   - tempoanalys
    #

    def analyze(self, race):

        horses = race.horses

        position_scores = self._score_start_positions(horses)

        for horse in horses:

            chaos_index = position_scores.get(horse.number, 0)

            horse.set_metric("chaos_index", round(chaos_index, 1))

        kaosvarde = self._calculate_kaosvarde(horses)
        race.kaosvarde = kaosvarde

        print()
        print("=== Kaosanalys ===")

        for horse in horses:
            print(
                f"{horse.number:>2}. {horse.name:<20} "
                f"spår:{horse.start_position!s:<4} "
                f"Kaos Index: {horse.get_metric('chaos_index')}"
            )

        print()
        print(f"Kaosvärde för loppet: {kaosvarde} ({self._kaosvarde_label(kaosvarde)})")

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
