"""
Jamfor leg["horses"] (troligen hela faltets roster) mot
leg["chosen_numbers"] (troligen det riktiga urvalet) for att
bekrafta vilket falt som faktiskt representerar systemets val.

Kor fran projektroten:
    python script/compare_horses_vs_chosen.py <prediction_id>
"""

import sys
import os
import json

PREDICTIONS_DIR = "data/races"


def main():
    if len(sys.argv) < 2:
        print("Anvandning: python script/compare_horses_vs_chosen.py <prediction_id>")
        return

    prediction_id = sys.argv[1]
    path = os.path.join(PREDICTIONS_DIR, f"{prediction_id}.json")

    if not os.path.exists(path):
        print(f"Hittar inte {path}")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    for leg in sorted(data["legs"], key=lambda l: l["race_number"]):
        horses_numbers = [h["number"] for h in leg["horses"]]
        chosen_numbers = leg.get("chosen_numbers")
        print(f"V{leg['race_number']}:")
        print(f"  horses (falt-roster?)     : {horses_numbers}")
        print(f"  chosen_numbers (urval?)   : {chosen_numbers}")
        print()


if __name__ == "__main__":
    main()
