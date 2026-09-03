"""
KAMT v2: kopplar ihop Niva 1 (baslinje), Niva 2 (matriserna A-D +
korstabell-mekanismen) och Niva 3 (Monte Carlo-motorn) till en
fullstandig analys av ett riktigt lopp.

Placerad har tillfalligt i projektroten - hor egentligen hemma i
modules/trav/ (Lager 3) enligt 003_Restructuring_Plan.md, flyttas
dit i ett senare migreringssteg.
"""

from foundation.database_manager import get_default_manager
from analysis_engine.baseline import BaselineCalculator
from analysis_engine.coupling_matrix_a import PositionMatrix
from analysis_engine.coupling_matrix_b import TrackWeatherMatrix
from analysis_engine.coupling_matrix_c import IncidentRiskMatrix
from analysis_engine.coupling_matrix_d import EquipmentMatrix
from analysis_engine.cross_matrix_effects import CrossMatrixEffects
from analysis_engine.monte_carlo_engine import MonteCarloEngine
from trav_race_simulator import TravRaceSimulator


#
# Antagen galoppfrekvens (0-1) for hastar utan tillrackligt med
# egen historik. Ovprovat - samma forsiktighet som ovriga
# matrisvarden i 004_KAMT_v2_Monte_Carlo_Design.md.
#
DEFAULT_GALLOP_RATE = 0.05

#
# Tak for en enskild hasts galoppsannolikhet i en given
# simulering, oavsett hur manga riskfaktorer som staplas -
# forhindrar orimliga varden vid extrem multiplikatorstapling.
#
MAX_GALLOP_PROBABILITY = 0.90


class RaceAnalyzer:
    #
    # Binder ihop hela KAMT v2-kedjan for ett riktigt lopp:
    #
    #   1. Niva 1: varje hasts egen baslinje (BaselineCalculator)
    #   2. Niva 2: Matris A (spetschans), B (bana/vader-effekt),
    #      C (galoppriskmultiplikator), D (utrustningseffekt +
    #      ev. skoandringstrigger), samt korstabell-justeringen
    #      via CrossMatrixEffects
    #   3. Niva 3: TravRaceSimulator kors genom den generella
    #      MonteCarloEngine, aggregerat till en
    #      sannolikhetsfordelning per hast
    #

    def __init__(self, db_manager=None, n_simulations=10000, noise_std=0.01, random_seed=None):
        self.db = db_manager or get_default_manager()
        self.baseline_calc = BaselineCalculator(self.db)
        self.matrix_a = PositionMatrix()
        self.matrix_b = TrackWeatherMatrix()
        self.matrix_c = IncidentRiskMatrix()
        self.matrix_d = EquipmentMatrix()
        self.cross_effects = CrossMatrixEffects()
        self.n_simulations = n_simulations
        self.noise_std = noise_std
        self.random_seed = random_seed

    def analyze(self, race, weather=None):
        #
        # race: ett Race-objekt (models/race.py) med .horses,
        #       .distance, .track_condition, .start_method, .date
        # weather: dict enligt samma format som
        #          analysis_data.weather ({"precipitation_mm": ...}),
        #          eller None
        #
        # Returnerar {horse_number: sannolikhet_procent}, eller
        # None om INGEN hast i loppet hade tillrackligt med
        # historik for en egen baslinje (loppet kan da inte
        # simuleras meningsfullt).
        #
        precipitation_mm = (weather or {}).get("precipitation_mm", 0)

        horses_context = []

        for horse in race.horses:
            baseline = self.baseline_calc.horse_baseline_seconds(
                horse.name, target_distance=race.distance
            )

            matrix_b_effect = self.matrix_b.effect(
                race.distance, race.track_condition, precipitation_mm
            )

            prev_front, prev_back = self.db.horse_previous_shoes(horse.name, race.date)
            trigger = self.matrix_d.shoe_change_trigger(
                previous_shod_front=prev_front, previous_shod_back=prev_back,
                current_shod_front=horse.shod_front, current_shod_back=horse.shod_back,
                track_condition=race.track_condition, precipitation_mm=precipitation_mm,
            )

            if trigger["effect"] is not None:
                matrix_d_effect = trigger["effect"]
            else:
                matrix_d_effect = self.matrix_d.base_effect(
                    race.track_condition, horse.shod_front, horse.shod_back,
                    horse.cart_type, race.distance,
                )

            c_multiplier = self.matrix_c.risk_multiplier(
                horse.start_position, race.start_method, race.track_condition
            )
            c_multiplier = self.cross_effects.apply(c_multiplier, trigger["flags"])

            gallop_safety = self.db.gallop_risk_score(horse.name)
            base_gallop_rate = (
                1 - gallop_safety / 100 if gallop_safety is not None
                else DEFAULT_GALLOP_RATE
            )
            gallop_probability = min(base_gallop_rate * c_multiplier, MAX_GALLOP_PROBABILITY)

            spets_score = self.matrix_a.spets_score(
                horse.start_position, horse.driver_win_pct, race.start_method
            )

            horses_context.append({
                "number": horse.number,
                "baseline_seconds": baseline,
                "matrix_b_effect": matrix_b_effect,
                "matrix_d_effect": matrix_d_effect,
                "spets_score": spets_score,
                "gallop_probability": gallop_probability,
            })

        #
        # Fallback for hastar utan egen baslinje: faltets snitt
        # bland de hastar i loppet som HAR data. Om ingen enda
        # hast har tillrackligt med historik kan loppet inte
        # simuleras meningsfullt alls.
        #
        known_baselines = [
            h["baseline_seconds"] for h in horses_context
            if h["baseline_seconds"] is not None
        ]

        if not known_baselines:
            return None

        field_average_baseline = sum(known_baselines) / len(known_baselines)

        for h in horses_context:
            if h["baseline_seconds"] is None:
                h["baseline_seconds"] = field_average_baseline

        simulator = TravRaceSimulator(horses_context, noise_std=self.noise_std)
        engine = MonteCarloEngine(
            n_simulations=self.n_simulations, random_seed=self.random_seed
        )

        return engine.run(simulator.run_single_simulation)
