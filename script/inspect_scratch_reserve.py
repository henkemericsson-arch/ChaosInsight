"""
Undersoker ATG:s ravdata for ett specifikt lopp i ett spel, med
fokus pa strukningar och eventuell reservordning - for att hitta
var/hur ATG anger vilken hast som ersatter en struken hast.

Kor fran projektroten:
    python script/inspect_scratch_reserve.py <prediction_id> <race_number>

Exempel:
    python script/inspect_scratch_reserve.py V85_2026-09-06_7_5__continuous__20260906T100816647614 6
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.atg_client import ATGClient

PREDICTIONS_DIR = "data/races"


def main():
    if len(sys.argv) < 3:
        print("Anvandning: python script/inspect_scratch_reserve.py <prediction_id> <race_number>")
        return

    prediction_id = sys.argv[1]
    race_number = int(sys.argv[2])

    path = os.path.join(PREDICTIONS_DIR, f"{prediction_id}.json")
    if not os.path.exists(path):
        print(f"Hittar inte {path}")
        return

    with open(path, encoding="utf-8") as f:
        prediction = json.load(f)

    leg = next((l for l in prediction["legs"] if l["race_number"] == race_number), None)
    if leg is None:
        print(f"Hittade inget lopp med race_number={race_number} i den sparade filen.")
        return

    race_id = leg.get("race_id")
    game_id = prediction.get("game_id")
    print(f"game_id={game_id}, race_id={race_id}")

    client = ATGClient()

    print("\n=== HELA SPELET - letar efter loppet i races-listan ===")
    game_data = client.get_game(game_id)
    raw_races = game_data.get("races", [])

    matching_race = None
    for index, r in enumerate(raw_races, start=1):
        if r.get("id") == race_id or index == race_number:
            matching_race = r
            print(f"Traff pa listposition {index} (race_number vi letar efter: {race_number})")
            break

    if matching_race is None:
        print("Hittade inget matchande lopp i races-listan.")
        return

    print("\n=== TOPPNIVA-FALT I LOPPET ===")
    print(list(matching_race.keys()))

    #
    # Skriv ut ALLA toppnivafalt i loppet FORUTOM starts (som vi
    # tar separat nedan) - for att se om reservordning ligger pa
    # looppniva.
    #
    print("\n=== LOPPETS EGNA FALT (utan starts) ===")
    race_without_starts = {k: v for k, v in matching_race.items() if k != "starts"}
    print(json.dumps(race_without_starts, indent=2, ensure_ascii=False))

    print("\n=== VARJE STARTS FALT (sokr efter struken/reserv-info) ===")
    for start in matching_race.get("starts", []):
        print(f"\n--- Startnummer {start.get('number')} ---")
        print(json.dumps(start, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
