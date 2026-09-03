"""
KAMT v2: den travspecifika scenario-funktionen som
analysis_engine.monte_carlo_engine.MonteCarloEngine anropar en
gang per simulering.

Placerad har tillfalligt i projektroten - hor egentligen hemma i
modules/trav/ (Lager 3) enligt 003_Restructuring_Plan.md, men den
mappen ar annu inte byggd (steg 4 i migreringsordningen). Flyttas
dit utan andrad logik nar det steget genomfors.
"""

from analysis_engine.coupling_matrix_a import PositionMatrix


class TravRaceSimulator:
    #
    # Tvafasmodell for en enskild simulering (se
    # 004_KAMT_v2_Monte_Carlo_Design.md, oppen fraga 3):
    #
    #   Fas 1 (Startkampen): en viktad slumpdragning bland
    #   hastarna, viktad mot deras Matris A-"spetschans",
    #   avgor vem som tar ledningen i just den har korningen.
    #
    #   Fas 2 (Kapacitetsberakning): varje hasts justerade tid
    #   for korningen = baslinje x (1 - summan av tillampliga
    #   matriseffekter, inklusive positionseffekt och brus).
    #   Lagst justerad tid vinner den enskilda korningen.
    #
    # Galoppkontroll: varje hast har en gallop_probability
    # (fran Matris C, ev. justerad av cross_matrix_effects) -
    # slar den in, ar hasten ur just den har korningen.
    #

    def __init__(self, horses_context, noise_std=0.01):
        #
        # horses_context: lista av dictar, en per hast, med
        # minst:
        #   number             - hastens nummer (identifierare)
        #   baseline_seconds   - Niva 1, fran BaselineCalculator
        #   matrix_b_effect    - fran TrackWeatherMatrix
        #   matrix_d_effect    - fran EquipmentMatrix
        #   spets_score        - fran PositionMatrix
        #   gallop_probability - 0.0-1.0, fran gallop_risk_score
        #                        + IncidentRiskMatrix (+ ev.
        #                        cross_matrix_effects-justering)
        #
        self.horses = horses_context
        self.noise_std = noise_std

    def run_single_simulation(self, rng):
        if not self.horses:
            return None

        weights = [h.get("spets_score", 0.1) for h in self.horses]
        lead_winner = self._weighted_choice(rng, self.horses, weights)
        runner_up = self._runner_up(lead_winner)

        best_time = None
        winner_number = None

        for horse in self.horses:
            gallop_probability = horse.get("gallop_probability", 0.0) or 0.0
            if rng.random() < gallop_probability:
                #
                # Galopperade i just den har simuleringen -
                # ur kampen om vinsten denna gang.
                #
                continue

            total_effect = (
                (horse.get("matrix_b_effect") or 0.0)
                + (horse.get("matrix_d_effect") or 0.0)
            )

            if horse is lead_winner:
                total_effect += PositionMatrix.LEAD_BONUS
            elif horse is runner_up:
                #
                # Forsokte ta ledningen (nast hogst spetschans)
                # men forlorade - hamnar i "dodens".
                #
                total_effect += PositionMatrix.DOOM_PENALTY

            total_effect += rng.gauss(0, self.noise_std)

            baseline = horse.get("baseline_seconds")
            if baseline is None:
                continue

            adjusted_time = baseline * (1 - total_effect)

            if best_time is None or adjusted_time < best_time:
                best_time = adjusted_time
                winner_number = horse["number"]

        return winner_number

    def _runner_up(self, winner):
        candidates = [h for h in self.horses if h is not winner]
        if not candidates:
            return None
        return max(candidates, key=lambda h: h.get("spets_score", 0))

    @staticmethod
    def _weighted_choice(rng, items, weights):
        total = sum(weights)
        if total <= 0:
            return rng.choice(items)

        r = rng.uniform(0, total)
        upto = 0
        for item, weight in zip(items, weights):
            upto += weight
            if upto >= r:
                return item

        return items[-1]
