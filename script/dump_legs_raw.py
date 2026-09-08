"""
Rå utskrift av race_number och antal/lista hastar per lopp i en
sparad fil - ingen tolkning, bara raw data - for att felsoka en
motsagelse mellan tva tidigare diagnosresultat.

Kor fran projektroten:
    python script/dump_legs_raw.py <prediction_id>
"""

import sys
import os
import json

PREDICTIONS_DIR = "data/races"


def main():
    if len(sys.argv) < 2:
        print("Anvandning: python script/dump_legs_raw.py <prediction_id>")
        return

    prediction_id = sys.argv[1]
    path = os.path.join(PREDICTIONS_DIR, f"{prediction_id}.json")

    if not os.path.exists(path):
        print(f"Hittar inte {path}")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    for leg in data["legs"]:
        horse_numbers = [h["number"] for h in leg["horses"]]
        print(f"race_number={leg['race_number']!r}  antal_hastar={len(horse_numbers)}  hastar={horse_numbers}")


if __name__ == "__main__":
    main()
