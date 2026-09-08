"""
Visar odds OCH streckprocent for ALLA hastar i ett specifikt lopp
(inte bara de som blev valda i systemet) - for att jamfora vilket
matt som faktiskt pekar ut favoriten.

Kor fran projektroten:
    python script/inspect_leg_odds_vs_streck.py <prediction_id> <race_number>

Exempel:
    python script/inspect_leg_odds_vs_streck.py V64_2026-09-08_14_4__legacy__20260908T181427281765 3
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
        print("Anvandning: python script/inspect_leg_odds_vs_streck.py <prediction_id> <race_number>")
        return

    prediction_id = sys.argv[1]
    race_number = int(sys.argv[2])

    path = os.path.join(PREDICTIONS_DIR, f"{prediction_id}.json")
    if not os.path.exists(path):
        print(f"Hittar inte {path}")
        return

    with open(path, encoding="utf-8") as f:
        prediction = json.load(f)

    game_id = prediction.get("game_id")
    chosen_numbers = set()
    for leg in prediction["legs"]:
        if leg["race_number"] == race_number:
            chosen_numbers = {h["number"] for h in leg["horses"]}
            break

    print(f"game_id={game_id}, race_number={race_number}")
    print(f"Valda i det sparade systemet: {sorted(chosen_numbers)}\n")

    client = ATGClient()
    raw_game_data = client.get_game(game_id)

    race_parser = RaceParser()
    races = race_parser.parse(raw_game_data)

    race = next((r for r in races if r.race_number == race_number), None)
    if race is None:
        print(f"Hittade inget lopp med race_number={race_number}")
        return

    print(f"{'Nr':>3}  {'Namn':<25} {'Odds':>8}  {'Streck%':>8}  Vald?")
    print("-" * 60)

    sorted_by_odds = sorted(
        race.horses, key=lambda h: h.odds if h.odds is not None else 999999
    )

    for horse in sorted_by_odds:
        odds_str = f"{horse.odds}" if horse.odds is not None else "-"
        streck_str = f"{horse.bet_percentage}" if horse.bet_percentage is not None else "-"
        chosen_marker = "JA" if horse.number in chosen_numbers else ""
        print(f"{horse.number:>3}  {horse.name:<25} {odds_str:>8}  {streck_str:>8}  {chosen_marker}")

    print()
    print("Sorterat efter LAGST odds forst - jamfor mot streckprocenten bredvid.")
    print("Om ordningen skiljer sig mycket mellan de tva kolumnerna, forklarar det")
    print("varfor favoritgolvet (som anvander odds) kan missa en streckfavorit.")


if __name__ == "__main__":
    main()
