import os

from services.db import get_connection, init_db, DB_PATH


class HistoricalStatsProvider:
    #
    # Exponerar harledd per-hast-statistik som ChaosEngine anvander
    # for att fylla i KAMT-modellens historik-beroende komponenter
    # (distansstatistik, bana/underlag, galopprisk, tempoanalys).
    #
    # Fragar SQLite-databasen (data/history/chaosinsight.db) direkt
    # istallet for att - som tidigare - lasa in hela
    # backfill_starts.jsonl och observations.jsonl i minnet vid
    # start och linjarsoka i Python. Indexen i services/db.py gor
    # varje uppslagning snabb aven nar historiken vaxer.
    #
    # Alla metoder returnerar None om det inte finns tillrackligt
    # med historik for att saga nagot meningsfullt - anroparen
    # ansvarar for att falla tillbaka pa ett neutralt varde da
    # (se ChaosEngine).
    #
    # OBS betraffande tempo_differential: precis som i den tidigare
    # JSONL-baserade versionen bygger faltets snitt-km-tid bara pa
    # backfill_starts (observations-rader saknar race_number och
    # gick darfor aldrig in i den motsvarande indexeringen tidigare
    # heller) - detta ar oforandrat beteende, inte en ny begransning.
    #

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        if not os.path.exists(self.db_path):
            init_db(self.db_path)
        self._conn = get_connection(self.db_path)

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
        # finns. Slar ihop backfill- och observationsdata, precis
        # som tidigare.
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
        # OBS: detta ar en tidsdifferens i sekunder, inte redan
        # en 0-100-skala - ChaosEngine min-max-normaliserar
        # detta varde inom det aktuella loppets falt innan det
        # anvands.
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
                #
                # Inte tillrackligt med faltdata i just det
                # historiska loppet for att rakna ett meningsfullt
                # snitt.
                #
                continue

            field_avg = sum(field_times) / len(field_times)
            diffs.append(horse_seconds - field_avg)

        if not diffs:
            return None

        return round(sum(diffs) / len(diffs), 3)


#
# Enkel processminnescache sa att SQLite-anslutningen inte oppnas
# pa nytt vid varje loppanalys.
#
_default_provider = None


def get_default_provider():
    global _default_provider
    if _default_provider is None:
        _default_provider = HistoricalStatsProvider()
    return _default_provider
