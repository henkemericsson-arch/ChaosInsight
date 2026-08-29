"""
Engangsskript for att undersoka om ATG:s rådata (samma API-anrop
som appen redan gor via ATGClient) innehaller nagon fritext-
kommentar om hasten - t.ex. den typ av kort analystext som syns i
ATG-appen ("Tre raka segrar i varas...").

Kor fran projektroten:
    python script/inspect_horse_fields.py
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.atg_client import ATGClient
from config.bet_types import SYSTEM_BET_TYPES


def main():
    client = ATGClient()
    today = datetime.now().strftime("%Y-%m-%d")
    calendar = client.get_calendar(today)

    game_id = None
    game_name = None

    for track_day in calendar.days[0].track_days:
        for game in track_day.games:
            if game.name.upper() in SYSTEM_BET_TYPES:
                game_id = game.id
                game_name = game.name
                break
        if game_id:
            break

    if not game_id:
        print("Inget poolspel hittades for idag.")
        return

    print(f"Anvander spel: {game_name} ({game_id})")

    data = client.get_game(game_id)
    first_race = data.get("races", [])[0]
    first_start = first_race.get("starts", [])[0]

    print()
    print("=== ALLA TOPPNIVA-FALT FOR EN START ===")
    print(list(first_start.keys()))

    print()
    print("=== ALLA FALT INUTI horse-objektet ===")
    print(list((first_start.get("horse") or {}).keys()))

    print()
    print("=== HELA start-objektet (forsta hasten) ===")
    print(json.dumps(first_start, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
