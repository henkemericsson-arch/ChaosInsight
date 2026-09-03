import threading

from services.db import (
    get_connection,
    init_db,
    insert_row,
    DB_PATH,
    BACKFILL_COLUMNS,
    OBSERVATION_COLUMNS,
    KAMT_V2_FORECAST_COLUMNS,
)


class DatabaseManager:
    #
    # Enda vagen in till databasen. Ingen annan modul ska kora SQL
    # direkt eller kanna till databasschemat - se
    # Chaos_Insight_Bible.md grundprincip 3 ("Ingen modul far lasa
    # filer direkt. All filhantering gar via respektive manager.")
    # och 000_Blueprint.md Lager 1 (Foundation).
    #
    # Detta ar steg 1 i 003_Restructuring_Plan.md:s
    # migreringsordning - en tunn inlindning av den redan
    # centraliserade services/db.py. Ingen befintlig SQL-logik har
    # andrats har, bara flyttats hit fran historical_stats.py och
    # fix_xpress_corruption.py, som tidigare kande till
    # databasschemat direkt.
    #

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        #
        # init_db() ar sakert att kora aven om databasfilen redan
        # finns - alla CREATE-satser anvander IF NOT EXISTS. Maste
        # koras varje gang (inte bara nar filen saknas helt),
        # annars far en redan existerande databas aldrig nya
        # tabeller/index som laggs till i schemat senare (upptackt
        # nar kamt_v2_forecasts-tabellen lades till - befintliga
        # databaser fick den aldrig).
        #
        init_db(self.db_path)
        self._conn = get_connection(self.db_path)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ------------------------------------------------------------
    # Skrivvagar
    # ------------------------------------------------------------

    def insert_backfill_start(self, row, or_ignore=True):
        insert_row(self._conn, "backfill_starts", row, BACKFILL_COLUMNS, or_ignore=or_ignore)

    def insert_observation(self, row, or_ignore=True):
        insert_row(self._conn, "observations", row, OBSERVATION_COLUMNS, or_ignore=or_ignore)

    def insert_kamt_v2_forecast(self, row, or_ignore=True):
        #
        # KAMT v2 - skuggat/parallellt lage. Se
        # kamt_v2_forecast_logger.py. Paverkar inga riktiga
        # systemval.
        #
        insert_row(self._conn, "kamt_v2_forecasts", row, KAMT_V2_FORECAST_COLUMNS, or_ignore=or_ignore)

    # ------------------------------------------------------------
    # Lasvagar - flyttade oforandrade fran historical_stats.py
    # ------------------------------------------------------------

    @staticmethod
    def _parse_km_time_seconds(km_time_str):
        #
        # Format "M.SS,T" (t.ex. "1.14,0") -> totalt antal
        # sekunder som flyttal.
        #
        if not km_time_str:
            return None

        try:
            minutes_part, rest = km_time_str.split(".")
            seconds_part, tenths_part = rest.split(",")

            minutes = int(minutes_part)
            seconds = int(seconds_part)
            tenths = int(tenths_part)

            return minutes * 60 + seconds + tenths / 10
        except (ValueError, AttributeError):
            return None

    def distance_score(self, horse_name, target_distance, margin=100):
        #
        # Vinstprocent (0-100) bland hastens historiska starter
        # inom distansmarginalen. None om ingen matchande start
        # finns. Slar ihop backfill- och observationsdata.
        #
        if target_distance is None:
            return None

        rows = self._conn.execute(
            """
            SELECT actual_finish_order FROM backfill_starts
            WHERE horse_name = ?
              AND distance IS NOT NULL
              AND ABS(distance - ?) <= ?
              AND (actual_scratched IS NULL OR actual_scratched = 0)
            UNION ALL
            SELECT actual_finish_order FROM observations
            WHERE horse_name = ?
              AND distance IS NOT NULL
              AND ABS(distance - ?) <= ?
              AND (actual_scratched IS NULL OR actual_scratched = 0)
            """,
            (horse_name, target_distance, margin, horse_name, target_distance, margin),
        ).fetchall()

        if not rows:
            return None

        wins = sum(1 for r in rows if r["actual_finish_order"] == 1)
        return round(100 * wins / len(rows), 1)

    def track_condition_score(self, horse_name, target_condition):
        #
        # Vinstprocent (0-100) bland hastens historiska starter
        # pa exakt samma bantyp. None om ingen matchande start
        # finns.
        #
        if not target_condition:
            return None

        rows = self._conn.execute(
            """
            SELECT actual_finish_order FROM backfill_starts
            WHERE horse_name = ?
              AND track_condition = ?
              AND (actual_scratched IS NULL OR actual_scratched = 0)
            UNION ALL
            SELECT actual_finish_order FROM observations
            WHERE horse_name = ?
              AND track_condition = ?
              AND (actual_scratched IS NULL OR actual_scratched = 0)
            """,
            (horse_name, target_condition, horse_name, target_condition),
        ).fetchall()

        if not rows:
            return None

        wins = sum(1 for r in rows if r["actual_finish_order"] == 1)
        return round(100 * wins / len(rows), 1)

    def gallop_risk_score(self, horse_name):
        #
        # 100 x (1 - galoppfrekvens) - fler galopper ger lagre
        # poang. None om hasten saknar historiska starter helt.
        #
        rows = self._conn.execute(
            """
            SELECT actual_galloped FROM backfill_starts
            WHERE horse_name = ?
              AND (actual_scratched IS NULL OR actual_scratched = 0)
            UNION ALL
            SELECT actual_galloped FROM observations
            WHERE horse_name = ?
              AND (actual_scratched IS NULL OR actual_scratched = 0)
            """,
            (horse_name, horse_name),
        ).fetchall()

        if not rows:
            return None

        gallops = sum(1 for r in rows if r["actual_galloped"])
        gallop_rate = gallops / len(rows)

        return round(100 * (1 - gallop_rate), 1)

    def tempo_differential(self, horse_name, target_distance, margin=100):
        #
        # Hastens genomsnittliga km-tid (sekunder) relativt
        # faltets snitt i samma historiska lopp, over starter
        # inom distansmarginalen. Negativt varde = hasten var i
        # snitt snabbare an faltet. None om otillracklig data.
        #
        # OBS: bygger bara pa backfill_starts (observations-rader
        # saknar race_number och gick darfor aldrig in i
        # motsvarande faltberakning i den tidigare JSONL-baserade
        # versionen heller) - oforandrat beteende.
        #
        if target_distance is None:
            return None

        starts = self._conn.execute(
            """
            SELECT game_id, race_number, actual_km_time
            FROM backfill_starts
            WHERE horse_name = ?
              AND (actual_scratched IS NULL OR actual_scratched = 0)
              AND (actual_galloped IS NULL OR actual_galloped = 0)
              AND (actual_disqualified IS NULL OR actual_disqualified = 0)
              AND distance IS NOT NULL
              AND ABS(distance - ?) <= ?
            """,
            (horse_name, target_distance, margin),
        ).fetchall()

        if not starts:
            return None

        diffs = []

        for s in starts:
            horse_seconds = self._parse_km_time_seconds(s["actual_km_time"])
            if horse_seconds is None:
                continue

            field_rows = self._conn.execute(
                """
                SELECT actual_km_time FROM backfill_starts
                WHERE game_id = ? AND race_number = ?
                  AND (actual_scratched IS NULL OR actual_scratched = 0)
                  AND actual_km_time IS NOT NULL
                """,
                (s["game_id"], s["race_number"]),
            ).fetchall()

            field_times = [
                self._parse_km_time_seconds(r["actual_km_time"])
                for r in field_rows
            ]
            field_times = [t for t in field_times if t is not None]

            if len(field_times) < 2:
                continue

            field_avg = sum(field_times) / len(field_times)
            diffs.append(horse_seconds - field_avg)

        if not diffs:
            return None

        return round(sum(diffs) / len(diffs), 3)

    # ------------------------------------------------------------
    # Diagnostik - flyttad oforandrad fran fix_xpress_corruption.py
    # ------------------------------------------------------------

    def horse_km_times(self, horse_name, target_distance=None, margin=100):
        #
        # Hastens egna giltiga km-tider (sekunder), for
        # baslinjeberakningen i analysis_engine/baseline.py
        # (KAMT v2 Niva 1). Till skillnad fran tempo_differential
        # behovs ingen faltjamforelse har, sa observations kan
        # anvandas har (den saknar bara race_number, som
        # tempo_differential behover for faltberakningen - inte
        # ett problem for en ren egen-tid-uppslagning).
        #
        distance_filter = ""
        params = [horse_name]

        if target_distance is not None:
            distance_filter = "AND distance IS NOT NULL AND ABS(distance - ?) <= ?"
            params.extend([target_distance, margin])

        query = f"""
            SELECT actual_km_time FROM backfill_starts
            WHERE horse_name = ?
              AND (actual_scratched IS NULL OR actual_scratched = 0)
              AND (actual_galloped IS NULL OR actual_galloped = 0)
              AND (actual_disqualified IS NULL OR actual_disqualified = 0)
              AND actual_km_time IS NOT NULL
              {distance_filter}
            UNION ALL
            SELECT actual_km_time FROM observations
            WHERE horse_name = ?
              AND (actual_scratched IS NULL OR actual_scratched = 0)
              AND (actual_galloped IS NULL OR actual_galloped = 0)
              AND (actual_disqualified IS NULL OR actual_disqualified = 0)
              AND actual_km_time IS NOT NULL
              {distance_filter}
        """

        all_params = params + params if target_distance is not None else [horse_name, horse_name]

        rows = self._conn.execute(query, all_params).fetchall()

        times = [self._parse_km_time_seconds(r["actual_km_time"]) for r in rows]
        return [t for t in times if t is not None]

    def horse_previous_shoes(self, horse_name, before_date):
        #
        # Hastens skoningsstatus (shod_front, shod_back) vid dess
        # narmast foregaende start fore ett givet datum. Behovs
        # for att Matris D (analysis_engine/coupling_matrix_d.py)
        # ska kunna avgora RIKTNINGEN pa en skoandring (skor->
        # barfota eller tvartom) - dagens rad har bara en boolean
        # for "skedde en andring", inte vilket hall.
        #
        # (None, None) om ingen tidigare start finns.
        #
        row = self._conn.execute(
            """
            SELECT shod_front, shod_back, date FROM (
                SELECT shod_front, shod_back, date FROM backfill_starts
                WHERE horse_name = ? AND date < ?
                  AND (actual_scratched IS NULL OR actual_scratched = 0)
                UNION ALL
                SELECT shod_front, shod_back, date FROM observations
                WHERE horse_name = ? AND date < ?
                  AND (actual_scratched IS NULL OR actual_scratched = 0)
            )
            ORDER BY date DESC
            LIMIT 1
            """,
            (horse_name, before_date, horse_name, before_date),
        ).fetchone()

        if row is None:
            return None, None

        return row["shod_front"], row["shod_back"]

    def find_corrupted_xpress_games(self):
        rows = self._conn.execute("""
            SELECT game_id, date, GROUP_CONCAT(DISTINCT track) as tracks
            FROM backfill_starts
            GROUP BY game_id
            HAVING COUNT(DISTINCT track) > 1
            ORDER BY date
        """).fetchall()

        affected = []
        for row in rows:
            collisions = self._conn.execute("""
                SELECT race_number FROM backfill_starts
                WHERE game_id = ?
                GROUP BY race_number
                HAVING COUNT(DISTINCT track) > 1
            """, (row["game_id"],)).fetchall()

            if collisions:
                affected.append({
                    "game_id": row["game_id"],
                    "date": row["date"],
                    "tracks": row["tracks"],
                })

        return affected

    def delete_backfill_rows_for_games(self, game_ids):
        if not game_ids:
            return 0
        placeholders = ",".join(["?"] * len(game_ids))
        cur = self._conn.execute(
            f"DELETE FROM backfill_starts WHERE game_id IN ({placeholders})",
            game_ids,
        )
        return cur.rowcount


#
# Tradlokal cache (INTE en global processomfattande singleton) -
# sa att lasintensiva sammanhang (t.ex. Flask-appens loppanalys)
# slipper oppna en ny anslutning vid varje uppslagning, samtidigt
# som varje trad garanterat far sin EGEN SQLite-anslutning.
#
# En vanlig global singleton (en enda delad self._conn) kraschar
# med "SQLite objects created in a thread can only be used in
# that same thread" sa fort mer an en trad anvander den - t.ex.
# Flask-appens forfragningstrad och bakgrundstraden for automatisk
# historikpafyllning (se _maybe_start_automatic_backfill() i
# web_app/app.py). threading.local() ger varje trad sin egen
# instans av samma delade cache-mekanism, utan att behova stanga
# av SQLite:s egen trad-sakerhetskontroll
# (sqlite3.connect(check_same_thread=False)), vilket bara hade
# dolt problemet istallet for att losa det.
#
# Skript som gor en avgransad korning (backfill, migrering)
# instansierar hellre DatabaseManager() direkt och stanger den nar
# de ar klara - oberoende av den har cachen.
#
_thread_local = threading.local()


def get_default_manager():
    if getattr(_thread_local, "manager", None) is None:
        _thread_local.manager = DatabaseManager()
    return _thread_local.manager
