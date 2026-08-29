import sqlite3
import os
import json

#
# Enda SQLite-filen for all historisk data (backfill + observationer
# fran Learning Engine). Ersatter de tva JSONL-filerna
# (backfill_starts.jsonl, observations.jsonl) som tidigare laddades
# in i sin helhet i minnet vid varje analys.
#
DB_PATH = "data/history/chaosinsight.db"

#
# Kolumnordning - anvands av backfill_history.py,
# learning_engine.py och migreringsskriptet for att bygga
# INSERT-satser utan att behova upprepa listan pa flera stallen.
#
BACKFILL_COLUMNS = [
    "game_id", "date", "track", "track_condition", "distance",
    "start_method", "race_number", "horse_number", "horse_name",
    "driver", "trainer", "start_position", "age", "sex", "odds",
    "bet_percentage", "shod_front", "shod_back", "shoe_changed",
    "sulky_changed", "cart_type", "career_earnings", "driver_win_pct",
    "trainer_win_pct", "horse_win_pct", "actual_finish_order",
    "actual_place", "actual_final_odds", "actual_scratched",
    "actual_galloped", "actual_disqualified", "actual_prize_money",
    "actual_km_time", "actual_km_time_status_code",
]

OBSERVATION_COLUMNS = [
    "logged_at", "game_id", "strategy", "race_id", "date", "track",
    "distance", "start_method", "track_condition", "kaosvarde",
    "weather", "horse_number", "horse_name", "driver", "trainer",
    "start_position", "odds", "bet_percentage", "shod_front",
    "shod_back", "shoe_changed", "sulky_changed", "cart_type",
    "career_earnings", "driver_win_pct", "trainer_win_pct",
    "horse_win_pct", "predicted_total_score", "predicted_crowd_index",
    "predicted_chaos_index", "predicted_expert_index",
    "chosen_by_system", "actual_finish_order", "actual_place",
    "actual_final_odds", "actual_scratched", "actual_galloped",
    "actual_disqualified", "actual_prize_money", "actual_km_time",
    "actual_km_time_status_code",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS backfill_starts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT, date TEXT, track TEXT, track_condition TEXT,
    distance INTEGER, start_method TEXT, race_number INTEGER,
    horse_number INTEGER, horse_name TEXT, driver TEXT, trainer TEXT,
    start_position INTEGER, age INTEGER, sex TEXT, odds REAL,
    bet_percentage REAL, shod_front TEXT, shod_back TEXT,
    shoe_changed INTEGER, sulky_changed INTEGER, cart_type TEXT,
    career_earnings REAL, driver_win_pct REAL, trainer_win_pct REAL,
    horse_win_pct REAL, actual_finish_order INTEGER,
    actual_place INTEGER, actual_final_odds REAL,
    actual_scratched INTEGER, actual_galloped INTEGER,
    actual_disqualified INTEGER, actual_prize_money REAL,
    actual_km_time TEXT, actual_km_time_status_code TEXT,
    UNIQUE(game_id, race_number, horse_number)
);

CREATE INDEX IF NOT EXISTS idx_backfill_horse_name
    ON backfill_starts(horse_name);
CREATE INDEX IF NOT EXISTS idx_backfill_game_race
    ON backfill_starts(game_id, race_number);
CREATE INDEX IF NOT EXISTS idx_backfill_distance
    ON backfill_starts(distance);
CREATE INDEX IF NOT EXISTS idx_backfill_track_condition
    ON backfill_starts(track_condition);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at TEXT, game_id TEXT, strategy TEXT, race_id TEXT,
    date TEXT, track TEXT, distance INTEGER, start_method TEXT,
    track_condition TEXT, kaosvarde REAL, weather TEXT,
    horse_number INTEGER, horse_name TEXT, driver TEXT, trainer TEXT,
    start_position INTEGER, odds REAL, bet_percentage REAL,
    shod_front TEXT, shod_back TEXT, shoe_changed INTEGER,
    sulky_changed INTEGER, cart_type TEXT, career_earnings REAL,
    driver_win_pct REAL, trainer_win_pct REAL, horse_win_pct REAL,
    predicted_total_score REAL, predicted_crowd_index REAL,
    predicted_chaos_index REAL, predicted_expert_index REAL,
    chosen_by_system INTEGER, actual_finish_order INTEGER,
    actual_place INTEGER, actual_final_odds REAL,
    actual_scratched INTEGER, actual_galloped INTEGER,
    actual_disqualified INTEGER, actual_prize_money REAL,
    actual_km_time TEXT, actual_km_time_status_code TEXT,
    UNIQUE(logged_at, game_id, race_id, horse_number)
);

CREATE INDEX IF NOT EXISTS idx_obs_horse_name
    ON observations(horse_name);
CREATE INDEX IF NOT EXISTS idx_obs_game_race
    ON observations(game_id, race_id);
"""


def get_connection(db_path=None):
    path = db_path or DB_PATH
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    #
    # WAL later Flask-appen lasa samtidigt som ett skript (t.ex.
    # backfill_history.py) skriver, utan att laser hela filen.
    #
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path=None):
    conn = get_connection(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def coerce_value(value):
    #
    # SQLite har ingen egen boolesk typ - lagra True/False som 1/0
    # sa att SQL-jamforelser (WHERE actual_scratched = 0) fungerar
    # konsekvent.
    #
    if isinstance(value, bool):
        return int(value)
    #
    # Vissa falt (t.ex. "weather") kan innehalla ett strukturerat
    # objekt istallet for en enkel strang/siffra. SQLite kan bara
    # lagra skalara varden - json-koda sadana varden till text sa
    # att ingen data tappas, istallet for att krascha.
    #
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def insert_row(conn, table, row, columns, or_ignore=False):
    verb = "INSERT OR IGNORE" if or_ignore else "INSERT"
    placeholders = ",".join(["?"] * len(columns))
    col_list = ",".join(columns)
    values = tuple(coerce_value(row.get(col)) for col in columns)
    conn.execute(
        f"{verb} INTO {table} ({col_list}) VALUES ({placeholders})",
        values,
    )
