#
# Parameterlagret (005 avsnitt 16). Idempotent: kan köras flera gånger.
# Körs från projektroten:  python script/patch_parameter_layer.py
#
# Ändrar:
#   services/db.py                     tabell parameter_sets, kolumn parameter_version
#   foundation/database_manager.py     läs-/skrivmetoder för parameter_sets
#   analysis/crowd_engine.py           vikter via ParameterProvider + delpoäng som mått
#   analysis/chaos_engine.py           vikter via ParameterProvider + delpoäng som mått
#   services/score_engine.py           vikter via ParameterProvider
#   services/prediction_logger.py      parameter_version i prediktionsfilen
#   services/learning_engine.py        parameter_version i observationer
#   learning/observation_reader.py     parameter_version i meta
#   web_app/app.py                     läser om aktiv uppsättning vid varje spelanalys
#
# Allt eller inget: om något ankare inte hittas skrivs ingen fil.
#
import sys

edits = {}      # path -> text
problems = []


def load(path):
    if path not in edits:
        with open(path, encoding="utf-8") as f:
            edits[path] = f.read()
    return edits[path]


def edit(path, label, marker, old, new):
    text = load(path)
    if marker in text:
        print(f"  {label}: redan gjort")
        return
    count = text.count(old)
    if count != 1:
        print(f"  {label}: KRÄVER HANDPÅLÄGGNING (ankare hittades {count} gånger)")
        problems.append((path, label))
        return
    edits[path] = text.replace(old, new, 1)
    print(f"  {label}: patchad")


print("Patchar parameterlagret ...")

# ---- services/db.py -------------------------------------------------------
P = "services/db.py"
edit(P, "db: kolumnlista", "PARAMETER_SET_COLUMNS",
     'SCHEMA = """\n',
     'PARAMETER_SET_COLUMNS = [\n'
     '    "version", "created_at", "parent", "status", "params", "reason", "evidence",\n'
     ']\n\n'
     'SCHEMA = """\n')
edit(P, "db: observationskolumn", '"metrics_json", "code_version", "parameter_version",',
     '    "metrics_json", "code_version",\n    "chosen_by_system",',
     '    "metrics_json", "code_version", "parameter_version",\n    "chosen_by_system",')
edit(P, "db: observationsschema", "code_version TEXT, parameter_version INTEGER,",
     "    metrics_json TEXT, code_version TEXT,",
     "    metrics_json TEXT, code_version TEXT, parameter_version INTEGER,")
edit(P, "db: tabell parameter_sets", "CREATE TABLE IF NOT EXISTS parameter_sets",
     "    UNIQUE(fetched_at, game_id, source, article_url)\n);\n\"\"\"",
     "    UNIQUE(fetched_at, game_id, source, article_url)\n);\n\n"
     "CREATE TABLE IF NOT EXISTS parameter_sets (\n"
     "    version INTEGER PRIMARY KEY,\n"
     "    created_at TEXT, parent INTEGER, status TEXT,\n"
     "    params TEXT, reason TEXT, evidence TEXT\n"
     ");\n\"\"\"")
edit(P, "db: migrate_schema", "ADD COLUMN parameter_version",
     '            conn.execute(f"ALTER TABLE observations ADD COLUMN {column} TEXT")\n    conn.commit()',
     '            conn.execute(f"ALTER TABLE observations ADD COLUMN {column} TEXT")\n'
     '    if "parameter_version" not in existing:\n'
     '        conn.execute("ALTER TABLE observations ADD COLUMN parameter_version INTEGER")\n'
     '    conn.commit()')

# ---- foundation/database_manager.py ---------------------------------------
P = "foundation/database_manager.py"
edit(P, "manager: import", "    PARAMETER_SET_COLUMNS,\n",
     "    EXPERT_ARTICLE_COLUMNS,\n)",
     "    EXPERT_ARTICLE_COLUMNS,\n    PARAMETER_SET_COLUMNS,\n)")
edit(P, "manager: metoder", "def insert_parameter_set",
     "    # ------------------------------------------------------------\n    # Lasvagar - flyttade",
     '''    # ------------------------------------------------------------
    # Parameteruppsattningar (Learning Engine, parameter_sets)
    # ------------------------------------------------------------

    def insert_parameter_set(self, row):
        insert_row(self._conn, "parameter_sets", row, PARAMETER_SET_COLUMNS)

    def parameter_sets(self):
        cursor = self._conn.execute("SELECT * FROM parameter_sets ORDER BY version")
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def parameter_set(self, version):
        cursor = self._conn.execute(
            "SELECT * FROM parameter_sets WHERE version = ?", (version,)
        )
        columns = [c[0] for c in cursor.description]
        row = cursor.fetchone()
        return dict(zip(columns, row)) if row else None

    def update_parameter_status(self, version, status):
        self._conn.execute(
            "UPDATE parameter_sets SET status = ? WHERE version = ?", (status, version)
        )

    # ------------------------------------------------------------
    # Lasvagar - flyttade''')

# ---- analysis/crowd_engine.py ---------------------------------------------
P = "analysis/crowd_engine.py"
edit(P, "crowd: import", "get_parameter_provider",
     "from analysis.modules.base_analyzer import BaseAnalyzer\n",
     "from analysis.modules.base_analyzer import BaseAnalyzer\n"
     "from learning.trav.parameters import get_provider as get_parameter_provider\n")
edit(P, "crowd: vikter", 'self.parameters.group("crowd")',
     """    ODDS_WEIGHT = 20
    STRECK_WEIGHT = 10
    TREND_WEIGHT = 10
    EXPERT_WEIGHT = 5

    def analyze(self, race):
        horses = race.horses
""",
     """    #
    # Vikterna (odds, streck, trend, expert) kommer från ParameterProvider;
    # baseline ligger i learning/trav/parameter_schema.py.
    #

    def __init__(self, parameters=None):
        self.parameters = parameters or get_parameter_provider()

    def analyze(self, race):
        horses = race.horses
        weights = self.parameters.group("crowd")
""")
edit(P, "crowd: beräkning", "crowd_odds_score",
     """        total_weight = self.ODDS_WEIGHT + self.STRECK_WEIGHT

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
""",
     """        total_weight = weights["odds"] + weights["streck"]

        if has_trend_data:
            total_weight += weights["trend"]

        if has_expert_data:
            total_weight += weights["expert"]

        for horse in horses:
            odds_score = odds_scores.get(horse.number, 0)
            streck_score = horse.bet_percentage or 0

            #
            # Delpoängen sparas som mått så att Learning Engine kan se
            # vad varje signal bidrog med (005 avsnitt 16.4).
            #
            horse.set_metric("crowd_odds_score", odds_score)
            horse.set_metric("crowd_streck_score", streck_score)

            weighted_sum = (
                (odds_score * weights["odds"])
                + (streck_score * weights["streck"])
            )

            if has_trend_data:
                trend_score = trend_scores.get(horse.number, 50.0)
                horse.set_metric("crowd_trend_score", trend_score)
                weighted_sum += trend_score * weights["trend"]

            if has_expert_data:
                expert_score = horse.get_metric("expert_index")
                weighted_sum += expert_score * weights["expert"]

            crowd_index = weighted_sum / total_weight
""")

# ---- analysis/chaos_engine.py ---------------------------------------------
P = "analysis/chaos_engine.py"
edit(P, "chaos: import", "get_parameter_provider",
     "from services.historical_stats import get_default_provider\n",
     "from services.historical_stats import get_default_provider\n"
     "from learning.trav.parameters import get_provider as get_parameter_provider\n")
edit(P, "chaos: vikter", 'self.parameters.group("chaos")',
     """    START_POSITION_WEIGHT = 8
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
""",
     """    #
    # Vikterna kommer från ParameterProvider; baseline ligger i
    # learning/trav/parameter_schema.py.
    #

    NEUTRAL_SCORE = 50
    DISTANCE_MARGIN = 100

    def __init__(self, historical_stats=None, parameters=None):
        self.historical_stats = historical_stats or get_default_provider()
        self.parameters = parameters or get_parameter_provider()

    def analyze(self, race):
        horses = race.horses
        weights = self.parameters.group("chaos")

        position_scores = self._score_start_positions(horses)

        total_weight = (
            weights["start_position"]
            + weights["driver_form"]
            + weights["horse_form"]
            + weights["trainer_form"]
            + weights["distance"]
            + weights["track_condition"]
            + weights["gallop_risk"]
            + weights["tempo"]
        )
""")
edit(P, "chaos: beräkning", "chaos_start_position_score",
     """            chaos_index = (
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
""",
     """            chaos_index = (
                (position_score * weights["start_position"])
                + (driver_score * weights["driver_form"])
                + (horse_score * weights["horse_form"])
                + (trainer_score * weights["trainer_form"])
                + (distance_score * weights["distance"])
                + (track_condition_score * weights["track_condition"])
                + (gallop_score * weights["gallop_risk"])
                + (tempo_score * weights["tempo"])
            ) / total_weight

            horse.set_metric("chaos_index", round(chaos_index, 1))
            horse.set_metric("data_coverage", f"{8 - missing}/8")

            #
            # Delpoängen sparas som mått (005 avsnitt 16.4). Saknad
            # komponent har fått neutralt värde, precis som i beräkningen.
            #
            horse.set_metric("data_coverage_n", 8 - missing)
            horse.set_metric("chaos_start_position_score", position_score)
            horse.set_metric("chaos_driver_form_score", driver_score)
            horse.set_metric("chaos_horse_form_score", horse_score)
            horse.set_metric("chaos_trainer_form_score", trainer_score)
            horse.set_metric("chaos_distance_score", distance_score)
            horse.set_metric("chaos_track_condition_score", track_condition_score)
            horse.set_metric("chaos_gallop_risk_score", gallop_score)
            horse.set_metric("chaos_tempo_score", tempo_score)
""")

# ---- services/score_engine.py ---------------------------------------------
P = "services/score_engine.py"
edit(P, "score: import", "get_parameter_provider",
     "class ScoreEngine:\n",
     "from learning.trav.parameters import get_provider as get_parameter_provider\n\n\n"
     "class ScoreEngine:\n")
edit(P, "score: vikter", 'self.parameters.group("score")',
     """    CROWD_WEIGHT = 0.50
    CHAOS_WEIGHT = 0.50

    def calculate(self, race):

        for horse in race.horses:
""",
     """    #
    # Vikterna kommer från ParameterProvider (score.crowd, score.chaos);
    # baseline 0,50 / 0,50 ligger i learning/trav/parameter_schema.py.
    #

    def __init__(self, parameters=None):
        self.parameters = parameters or get_parameter_provider()

    def calculate(self, race):

        weights = self.parameters.group("score")

        for horse in race.horses:
""")
edit(P, "score: beräkning", 'weights["crowd"]',
     """                (crowd_index * self.CROWD_WEIGHT)
                + (chaos_index * self.CHAOS_WEIGHT)""",
     """                (crowd_index * weights["crowd"])
                + (chaos_index * weights["chaos"])""")

# ---- services/prediction_logger.py ----------------------------------------
P = "services/prediction_logger.py"
edit(P, "logger: import", "get_parameter_provider",
     "from foundation.run_info import code_version, metrics_to_dict\n",
     "from foundation.run_info import code_version, metrics_to_dict\n"
     "from learning.trav.parameters import get_provider as get_parameter_provider\n")
edit(P, "logger: parameter_version", '"parameter_version": get_parameter_provider().version',
     '            "code_version": code_version(),\n',
     '            "code_version": code_version(),\n'
     '            "parameter_version": get_parameter_provider().version,\n')

# ---- services/learning_engine.py ------------------------------------------
P = "services/learning_engine.py"
edit(P, "engine: parameter_version", '"parameter_version": prediction.get("parameter_version")',
     '                "code_version": prediction.get("code_version"),\n',
     '                "code_version": prediction.get("code_version"),\n'
     '                "parameter_version": prediction.get("parameter_version"),\n')

# ---- learning/observation_reader.py ---------------------------------------
P = "learning/observation_reader.py"
edit(P, "reader: parameter_version", '"parameter_version": first.get("parameter_version")',
     '                "code_version": first.get("code_version"),\n',
     '                "code_version": first.get("code_version"),\n'
     '                "parameter_version": first.get("parameter_version"),\n')

# ---- web_app/app.py -------------------------------------------------------
P = "web_app/app.py"
edit(P, "app: import", "get_parameter_provider",
     "from expert.auto_collect import start_expert_collection\n",
     "from expert.auto_collect import start_expert_collection\n"
     "from learning.trav.parameters import get_provider as get_parameter_provider\n")
edit(P, "app: refresh", "get_parameter_provider().refresh()",
     "    analysis_data = collector.collect(game)\n",
     "    get_parameter_provider().refresh()\n    analysis_data = collector.collect(game)\n")

if problems:
    print()
    print("Inget ändrades. Skicka utskriften ovan så justeras patchen.")
    sys.exit(1)

for path, text in edits.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
print("Klart.")
