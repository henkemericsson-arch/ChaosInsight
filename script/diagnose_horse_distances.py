"""
Kollar vilka distanser en specifik hasts historiska starter
faktiskt kordes pa, PLUS struken/galopp/diskning-flaggorna - for
att avgora om en None-km-tid ar forvantad (struken/galopperad) eller
en genuin lucka i resultatdatan.

Kor fran projektroten:
    python script/diagnose_horse_distances.py "<hastnamn>"

Exempel:
    python script/diagnose_horse_distances.py "Purple Memory"
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from foundation.database_manager import get_default_manager


def main():
    if len(sys.argv) < 2:
        print('Anvandning: python script/diagnose_horse_distances.py "<hastnamn>"')
        return

    horse_name = sys.argv[1]
    db = get_default_manager()

    rows = db._conn.execute(
        """
        SELECT distance, actual_km_time, date, track, game_id,
               actual_scratched, actual_galloped, actual_disqualified,
               actual_finish_order, actual_km_time_status_code
        FROM backfill_starts
        WHERE horse_name = ?
        UNION ALL
        SELECT distance, actual_km_time, date, track, game_id,
               actual_scratched, actual_galloped, actual_disqualified,
               actual_finish_order, actual_km_time_status_code
        FROM observations
        WHERE horse_name = ?
        ORDER BY date DESC
        """,
        (horse_name, horse_name),
    ).fetchall()

    print(f"Alla rader i databasen for '{horse_name}':\n")

    if not rows:
        print("Inga rader alls hittades - hasten finns inte i databasen overhuvudtaget.")
        return

    for row in rows:
        flags = []
        if row["actual_scratched"]:
            flags.append("STRUKEN")
        if row["actual_galloped"]:
            flags.append("GALOPP")
        if row["actual_disqualified"]:
            flags.append("DISKAD")
        flags_str = ", ".join(flags) if flags else "inga flaggor"

        print(
            f"  {row['date']}  {row['track']:12s} {row['game_id']:20s} "
            f"distans={row['distance']}m  km_tid={row['actual_km_time']!r}  "
            f"placering={row['actual_finish_order']}  "
            f"km_tid_kod={row['actual_km_time_status_code']!r}  "
            f"[{flags_str}]"
        )


if __name__ == "__main__":
    main()
