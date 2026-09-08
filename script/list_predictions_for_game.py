"""
Listar alla sparade system for ett visst game_id, med strategi,
risk och totalkostnad - for att snabbt hitta ratt fil bland manga
liknande tidsstamplar utan att behova gissa.

Kor fran projektroten:
    python script/list_predictions_for_game.py <game_id>

Exempel:
    python script/list_predictions_for_game.py V64_2026-09-08_14_4
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PREDICTIONS_DIR = "data/races"


def main():
    if len(sys.argv) < 2:
        print("Anvandning: python script/list_predictions_for_game.py <game_id>")
        return

    game_id = sys.argv[1]

    matches = []
    for filename in sorted(os.listdir(PREDICTIONS_DIR)):
        if not filename.endswith(".json"):
            continue
        if not filename.startswith(game_id + "__"):
            continue

        path = os.path.join(PREDICTIONS_DIR, filename)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        selection = data.get("selection") or {}
        matches.append({
            "filename": filename[:-5],
            "strategy": data.get("strategy"),
            "risk": selection.get("risk"),
            "spikes": selection.get("spikes"),
            "locks": selection.get("locks"),
            "total_cost": data.get("total_cost"),
        })

    if not matches:
        print(f"Inga sparade filer hittades for {game_id}")
        return

    print(f"{len(matches)} sparade filer for {game_id}:\n")
    for m in matches:
        print(
            f"  strategi={m['strategy']:12s} risk={str(m['risk']):8s} "
            f"spikar={m['spikes']} lås={m['locks']} kostnad={m['total_cost']} kr"
        )
        print(f"    {m['filename']}")
        print()


if __name__ == "__main__":
    main()
