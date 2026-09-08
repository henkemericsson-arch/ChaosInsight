"""
Visar alla toppniva-falt (och deras varden, forutom sjalva
legs-listan) i en sparad prediction-fil - for att hitta det
RIKTIGA faltnamnet for risk, spikar och las, istallet for att
gissa.

Kor fran projektroten:
    python script/inspect_prediction_structure.py <prediction_id>
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PREDICTIONS_DIR = "data/races"


def main():
    if len(sys.argv) < 2:
        print("Anvandning: python script/inspect_prediction_structure.py <prediction_id>")
        return

    prediction_id = sys.argv[1]
    path = os.path.join(PREDICTIONS_DIR, f"{prediction_id}.json")

    if not os.path.exists(path):
        print(f"Hittar inte {path}")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    print("Toppniva-falt och varden (utom legs/evaluation_history):\n")
    for key, value in data.items():
        if key in ("legs", "evaluation_history"):
            print(f"  {key}: [{len(value)} poster, ej visat]")
            continue
        print(f"  {key}: {value!r}")


if __name__ == "__main__":
    main()
