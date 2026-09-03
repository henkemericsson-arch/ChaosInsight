"""
KAMT v2 - skuggat/parallellt lage.

Kor RaceAnalyzer for verkliga lopp och loggar den forutsagda
vinstsannolikheten per hast till en egen tabell
(kamt_v2_forecasts), helt separat fran allt som faktiskt styr
systemval (PredictionLogger, SystemGenerator).

Syftet ar att bygga en utvarderingsdatabas - forutsagd
sannolikhet vs faktiskt utfall - sa att KAMT v2 kan bevisa sig
mot KAMT v1 innan den nagonsin far paverka riktiga spelbeslut.
Se 004_KAMT_v2_Monte_Carlo_Design.md.

Placerad har tillfalligt i projektroten - hor egentligen hemma i
modules/trav/ (Lager 3) enligt 003_Restructuring_Plan.md.
"""

from datetime import datetime, timezone

from foundation.database_manager import get_default_manager
from race_analyzer import RaceAnalyzer


class KamtV2ForecastLogger:

    def __init__(self, db_manager=None, race_analyzer=None):
        self.db = db_manager or get_default_manager()
        self.analyzer = race_analyzer or RaceAnalyzer(db_manager=self.db)

    def log_race(self, race, game_id, weather=None):
        #
        # Kor RaceAnalyzer for ETT lopp och loggar resultatet.
        # Returnerar antalet loggade hastar, eller 0 om loppet
        # inte kunde simuleras (t.ex. ingen historik alls i
        # hela faltet).
        #
        logged_at = datetime.now(timezone.utc).isoformat()
        probabilities, logged_count = self._analyze_and_log(race, game_id, weather, logged_at)
        self.db.commit()
        return logged_count

    def log_game(self, races, game_id, weather=None):
        #
        # Kor och loggar KAMT v2 for ALLA lopp i ett spel pa en
        # gang - anvands nar ett system genereras, sa att den
        # skuggade prognosen kan visas bredvid det riktiga
        # KAMT v1-forslaget utan ett extra databasanrop.
        #
        # Returnerar {race_number: {horse_number: sannolikhet}}
        # for varje lopp som kunde simuleras - lopp utan
        # tillrackllig historik utelamnas tyst (samma princip
        # som annars: hellre inget svar an ett opalitligt).
        #
        logged_at = datetime.now(timezone.utc).isoformat()
        predictions_by_race = {}

        for race in races:
            probabilities, _ = self._analyze_and_log(race, game_id, weather, logged_at)
            if probabilities is not None:
                predictions_by_race[race.race_number] = probabilities

        self.db.commit()
        return predictions_by_race

    def _analyze_and_log(self, race, game_id, weather, logged_at):
        probabilities = self.analyzer.analyze(race, weather=weather)

        if probabilities is None:
            return None, 0

        logged_count = 0

        for horse in race.horses:
            probability = probabilities.get(horse.number)
            if probability is None:
                continue

            row = {
                "logged_at": logged_at,
                "game_id": game_id,
                "race_number": getattr(race, "race_number", None),
                "race_id": getattr(race, "race_id", None),
                "date": race.date,
                "track": race.track,
                "horse_number": horse.number,
                "horse_name": horse.name,
                "predicted_win_probability": probability,
                "n_simulations": self.analyzer.n_simulations,
            }

            self.db.insert_kamt_v2_forecast(row, or_ignore=True)
            logged_count += 1

        return probabilities, logged_count

    @staticmethod
    def top_pick(probabilities):
        #
        # Hjalpmetod: given {horse_number: sannolikhet}, returnerar
        # (horse_number, sannolikhet) for hasten med hogst
        # forutsagd vinstsannolikhet. None om tomt.
        #
        if not probabilities:
            return None
        best_number = max(probabilities, key=probabilities.get)
        return best_number, probabilities[best_number]
