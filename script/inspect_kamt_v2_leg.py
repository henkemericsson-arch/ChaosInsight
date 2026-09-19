"""
Visar alla hastar i ett specifikt lopp fran en sparad KAMT v2-fil,
med odds, for att identifiera marknadsfavoriten och jamfora mot
vilka hastar som faktiskt valdes i systemet.

Kor fran projektroten:
    python script/inspect_kamt_v2_leg.py <prediction_id> <race_number>
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.atg_client import ATGClient
from parsers.race_parser import RaceParser

PREDICTIONS_DIR = "data/races"


def main():
    if len(sys.argv) < 3:
        print("Anvandning: python script/inspect_kamt_v2_leg.py <prediction_id> <race_number>")
        return

    prediction_id = sys.argv[1]
    race_number = int(sys.argv[2])

    path = os.path.join(PREDICTIONS_DIR, f"{prediction_id}.json")
    with open(path, encoding="utf-8") as f:
        prediction = json.load(f)

    game_id = prediction.get("game_id")

    chosen_numbers = set()
    for leg in prediction["legs"]:
        if leg["race_number"] == race_number:
            chosen_numbers = {h["number"] for h in leg["horses"]}
            break

    client = ATGClient()
    raw_game_data = client.get_game(game_id)
    race_parser = RaceParser()
    races = race_parser.parse(raw_game_data)

    race = next((r for r in races if r.race_number == race_number), None)
    if race is None:
        print(f"Hittade inget lopp med race_number={race_number}")
        return

    sorted_by_odds = sorted(
        race.horses, key=lambda h: h.odds if h.odds is not None else 999999
    )

    print(f"V{race_number} - valda i KAMT v2-systemet: {sorted(chosen_numbers)}\n")
    print(f"{'Nr':>3}  {'Namn':<25} {'Odds':>8}  Vald?")
    print("-" * 50)
    for horse in sorted_by_odds:
        odds_str = f"{horse.odds}" if horse.odds is not None else "-"
        marker = "JA" if horse.number in chosen_numbers else ""
        print(f"{horse.number:>3}  {horse.name:<25} {odds_str:>8}  {marker}")


if __name__ == "__main__":
    main()
