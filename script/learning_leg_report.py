#
# Etapp 1b i Learning Engine: spik/lås-urval, kaosvärde och täckning.
# Körs från projektroten:  python script/learning_leg_report.py
#
# Läser bara - ändrar ingenting.
#
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foundation.database_manager import DatabaseManager
from learning.analysis.leg_analysis import (
    coverage_analysis,
    kaos_analysis,
    selection_analysis,
)
from learning.analysis.leg_report import format_leg_report
from learning.observation_reader import build_races
from learning.trav import settings

#
# Täckningen analyseras per sparad strategi (de väljer olika hästar),
# urval och kaos per modell (continuous/legacy delar Total Score).
#
COVERAGE_STRATEGIES = {
    "continuous": ("continuous",),
    "legacy": ("legacy",),
    "kamt_v2": ("kamt_v2",),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="första loppdatum, ÅÅÅÅ-MM-DD")
    parser.add_argument("--until", help="sista loppdatum, ÅÅÅÅ-MM-DD")
    parser.add_argument("--exclude-track", action="append", default=[])
    parser.add_argument("--include-gallop", action="store_true")
    parser.add_argument("--min-legs", type=int, default=4,
                        help="minst så många fullständiga lopp för att ett spel ska räknas")
    parser.add_argument("--json", help="skriv rapporten som JSON till denna fil")
    args = parser.parse_args()

    excluded = list(args.exclude_track)
    if not args.include_gallop:
        excluded.extend(settings.GALLOP_TRACKS)

    db = DatabaseManager()
    rows = db.observations_for_analysis()
    db.close()

    common = dict(
        excluded_tracks=excluded, since=args.since, until=args.until,
        distance_classes=settings.DISTANCE_CLASSES,
    )

    models, skipped = build_races(rows, settings.MODEL_STRATEGIES, **common)
    per_strategy, _ = build_races(rows, COVERAGE_STRATEGIES, **common)

    selection = {}
    kaos = {}
    for model, races in models.items():
        if not races:
            continue
        selection[model] = {
            "spike": selection_analysis(races, "spike", min_legs=args.min_legs),
            "lock": selection_analysis(races, "lock", min_legs=args.min_legs),
        }
        kaos[model] = kaos_analysis(races)

    coverage = {s: coverage_analysis(r) for s, r in per_strategy.items() if r}

    print(f"Läste {len(rows)} observationsrader.")
    print(format_leg_report(selection, kaos, coverage, "alla lopp", skipped=skipped))

    path = args.json
    if path is None:
        os.makedirs("data/reports", exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = f"data/reports/legs_{stamp}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"selection": selection, "kaos": kaos, "coverage": coverage},
            f, ensure_ascii=False, indent=2,
        )
    print(f"\nRapport sparad som JSON: {path}")


if __name__ == "__main__":
    main()
