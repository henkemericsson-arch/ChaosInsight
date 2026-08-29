"""
Engangsskript som flyttar den befintliga historiska datan fran
data/history/backfill_starts.jsonl och data/history/observations.jsonl
in i den nya SQLite-databasen (data/history/chaosinsight.db).

Kor EN GANG, fran projektroten:
    python script/migrate_jsonl_to_sqlite.py

Skriptet tar INTE bort eller skriver over de gamla .jsonl-filerna -
de ligger kvar orörda som en extra sakerhetskopia tills du sjalv
verifierat att migreringen ser korrekt ut (t.ex. via /installningar
eller genom att jamfora radantal).
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.db import (
    get_connection,
    init_db,
    insert_row,
    DB_PATH,
    BACKFILL_COLUMNS,
    OBSERVATION_COLUMNS,
)

BACKFILL_PATH = "data/history/backfill_starts.jsonl"
OBSERVATIONS_PATH = "data/history/observations.jsonl"

BATCH_SIZE = 5000


def migrate_file(path, table, columns, conn):
    if not os.path.exists(path):
        print(f"[Migrering] {path} finns inte, hoppar over.")
        return 0

    count = 0
    skipped = 0

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            insert_row(conn, table, row, columns, or_ignore=True)
            count += 1

            if count % BATCH_SIZE == 0:
                conn.commit()
                print(f"[Migrering] {table}: {count} rader klara...")

    conn.commit()

    if skipped:
        print(f"[Migrering] {table}: hoppade over {skipped} trasiga rader.")

    return count


def main():
    if os.path.exists(DB_PATH):
        print(f"OBS: {DB_PATH} finns redan.")
        print("Kor du migreringen igen ignoreras dubbletter automatiskt")
        print("(via INSERT OR IGNORE), men det ar sakrast att bara kora")
        print("det har skriptet en gang.")
        answer = input("Fortsatt anda? (skriv 'ja' for att fortsatta): ")
        if answer.strip().lower() != "ja":
            print("Avbrutet.")
            return

    init_db()
    conn = get_connection()

    print("Migrerar backfill_starts.jsonl...")
    backfill_count = migrate_file(
        BACKFILL_PATH, "backfill_starts", BACKFILL_COLUMNS, conn
    )

    print("Migrerar observations.jsonl...")
    obs_count = migrate_file(
        OBSERVATIONS_PATH, "observations", OBSERVATION_COLUMNS, conn
    )

    row_count_backfill = conn.execute(
        "SELECT COUNT(*) AS c FROM backfill_starts"
    ).fetchone()["c"]
    row_count_obs = conn.execute(
        "SELECT COUNT(*) AS c FROM observations"
    ).fetchone()["c"]

    conn.close()

    print()
    print("=" * 60)
    print(f"Klart.")
    print(f"  backfill_starts.jsonl -> {backfill_count} rader lasta, {row_count_backfill} rader i databasen")
    print(f"  observations.jsonl    -> {obs_count} rader lasta, {row_count_obs} rader i databasen")
    print(f"Databas: {DB_PATH}")
    print()
    print("De gamla .jsonl-filerna ar orörda. Radera dem inte forran du")
    print("sjalv verifierat att radantalen ovan ser rimliga ut.")
    print("=" * 60)


if __name__ == "__main__":
    main()
