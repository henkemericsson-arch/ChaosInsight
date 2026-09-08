"""
Jamfor de tva olika ATG-endpointerna Learning Engine respektive
var tidigare diagnos anvande, for att se om
get_race_result(race_id) (racens "extended"-endpoint) faktiskt
innehaller samma pool-data (scratchings, reserveOrder) som
get_game(game_id) (hela spelets endpoint) gor.

Kor fran projektroten:
    python script/compare_result_endpoints.py <game_id> <race_id> <game_type>

Exempel:
    python script/compare_result_endpoints.py V85_2026-09-06_7_5 2026-09-06_7_10 V85
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.atg_client import ATGClient


def main():
    if len(sys.argv) < 4:
        print("Anvandning: python script/compare_result_endpoints.py <game_id> <race_id> <game_type>")
        return

    game_id = sys.argv[1]
    race_id = sys.argv[2]
    game_type = sys.argv[3]

    client = ATGClient()

    print("=== VAG 1: get_race_result(race_id) - det Learning Engine anvander ===")
    race_result_data = client.get_race_result(race_id)
    if race_result_data is None:
        print("get_race_result returnerade None!")
    else:
        print("Toppniva-falt:", list(race_result_data.keys()))
        print("result.scratchings:", (race_result_data.get("result") or {}).get("scratchings"))
        pools1 = race_result_data.get("pools") or {}
        print("Pooler som finns:", list(pools1.keys()))
        pool1 = pools1.get(game_type) or {}
        print(f"pools.{game_type}:", json.dumps(pool1, indent=2, ensure_ascii=False))

    print("\n=== VAG 2: get_game(game_id) - det var tidigare diagnos anvande ===")
    game_data = client.get_game(game_id)
    raw_races = game_data.get("races", [])
    matching_race = next((r for r in raw_races if r.get("id") == race_id), None)

    if matching_race is None:
        print("Hittade inget matchande lopp via get_game.")
    else:
        print("Toppniva-falt:", list(matching_race.keys()))
        print("result.scratchings:", (matching_race.get("result") or {}).get("scratchings"))
        pools2 = matching_race.get("pools") or {}
        print("Pooler som finns:", list(pools2.keys()))
        pool2 = pools2.get(game_type) or {}
        print(f"pools.{game_type}:", json.dumps(pool2, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
