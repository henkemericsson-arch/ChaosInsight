"""
Hittar och rensar korrupt historisk data orsakad av den tidigare
race_number-kollisionsbuggen (nar ett spel delas mellan tva banor,
t.ex. V86 Xpress pa onsdagar - Solvalla och Åby kunde bada ha ett
"lopp 7" samma kvall, vilket kolliderade i den gamla koden).

Kor fran projektroten:
    python script/fix_xpress_corruption.py

Visar forst vilka spel/datum som ar paverkade, utan att andra
nagot. Fragar om bekraftelse innan nagon rad raderas.

Efter radering: kor om
    python script/backfill_history.py
for att hamta om korrekt data for just de paverkade datumen (ovriga
redan backfillade datum paverkas inte och hoppas over som vanligt).

OBS: bara backfill_starts-tabellen paverkas av denna bugg.
observations-tabellen nyckla aldrig pa race_number (bara race_id,
som alltid varit korrekt unikt per bana) och behover darfor inte
rensas.

Anvander foundation.database_manager.DatabaseManager - kanner inte
langre till databasschemat direkt.
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from foundation.database_manager import DatabaseManager
from services.db import DB_PATH

PROGRESS_PATH = "data/history/backfill_progress.json"


def main():
    if not os.path.exists(DB_PATH):
        print(f"Ingen databas hittades pa {DB_PATH}.")
        return

    db = DatabaseManager()
    affected = db.find_corrupted_xpress_games()

    if not affected:
        print("Inga spel med race_number-kollision hittades. Datan ser ren ut.")
        db.close()
        return

    print(f"Hittade {len(affected)} spel med korrupt data (race_number-kollision mellan banor):\n")
    for game in affected:
        print(f"  {game['date']}  {game['game_id']:30s}  banor: {game['tracks']}")

    affected_dates = sorted({g["date"] for g in affected})
    affected_game_ids = [g["game_id"] for g in affected]

    print(f"\nBerör {len(affected_dates)} unika datum:")
    for d in affected_dates:
        print(f"  {d}")

    answer = input(
        f"\nRadera dessa {len(affected_game_ids)} spels rader fran databasen "
        f"och markera datumen for ombackfill? (skriv 'ja' for att fortsatta): "
    )
    if answer.strip().lower() != "ja":
        print("Avbrutet - ingenting andrat.")
        db.close()
        return

    deleted_rows = db.delete_backfill_rows_for_games(affected_game_ids)
    db.commit()
    db.close()

    print(f"\nRaderade {deleted_rows} rader fran backfill_starts.")

    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, encoding="utf-8") as f:
            progress = json.load(f)

        before_dates = len(progress.get("processed_dates", []))
        before_games = len(progress.get("processed_game_ids", []))

        progress["processed_dates"] = [
            d for d in progress.get("processed_dates", [])
            if d not in affected_dates
        ]
        progress["processed_game_ids"] = [
            g for g in progress.get("processed_game_ids", [])
            if g not in affected_game_ids
        ]

        with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

        removed_dates = before_dates - len(progress["processed_dates"])
        removed_games = before_games - len(progress["processed_game_ids"])
        print(
            f"Uppdaterade progressfilen: {removed_dates} datum och "
            f"{removed_games} spel-id:n markerade for ombackfill."
        )
    else:
        print("OBS: ingen progressfil hittades - inget att aterstalla dar.")

    print()
    print("=" * 60)
    print("Klart. Kor nu om backfill for att hamta om korrekt data:")
    print("    python script/backfill_history.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
