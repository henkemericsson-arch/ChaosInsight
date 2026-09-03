"""
Testar ATGClient.get_race_result() direkt for varje lopp i ett
sparat system, for att se exakt vilka lopp som lyckas/misslyckas
och varfor - istallet for att gissa utifran Learning Engine:s
"ej avgjort"-utskrift.

Kor fran projektroten:
    python script/diagnose_result_fetch.py <prediction_id>

<prediction_id> ar filnamnet i data/races/ UTAN .json, t.ex.:
    V85_2026-08-30_55_5__legacy__20260830T153649883598
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.atg_client import ATGClient

PREDICTIONS_DIR = "data/races"


def main():
    if len(sys.argv) < 2:
        print("Anvandning: python script/diagnose_result_fetch.py <prediction_id>")
        return

    prediction_id = sys.argv[1]
    path = os.path.join(PREDICTIONS_DIR, f"{prediction_id}.json")

    if not os.path.exists(path):
        print(f"Hittar inte {path}")
        return

    with open(path, encoding="utf-8") as f:
        prediction = json.load(f)

    client = ATGClient()

    for leg in sorted(prediction["legs"], key=lambda l: l["race_number"]):
        race_number = leg["race_number"]
        race_id = leg.get("race_id")

        print(f"=== V{race_number} - race_id={race_id!r} ===")

        if race_id is None:
            print("  race_id saknas helt i den sparade filen!\n")
            continue

        try:
            raw_data = client.get_race_result(race_id)
        except Exception as exc:
            print(f"  UNDANTAG vid hamtning: {exc!r}\n")
            continue

        if raw_data is None:
            print("  get_race_result() returnerade None (ingen data alls)\n")
            continue

        status = raw_data.get("status")
        print(f"  status-falt: {status!r}")
        print(f"  toppniva-falt i svaret: {list(raw_data.keys())}")

        starts = raw_data.get("starts", [])
        if starts:
            first_result = starts[0].get("result")
            print(f"  forsta startens 'result'-falt: {first_result!r}")

        print()


if __name__ == "__main__":
    main()
