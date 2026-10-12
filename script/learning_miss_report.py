#
# Etapp 3 i Learning Engine: missanalys på de egna prediktionerna.
# Körs från projektroten:  python script/learning_miss_report.py
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
from learning.analysis.miss_analysis import miss_analysis
from learning.analysis.miss_report import format_miss_report
from learning.observation_reader import build_races
from learning.trav import settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="första loppdatum, ÅÅÅÅ-MM-DD")
    parser.add_argument("--until", help="sista loppdatum, ÅÅÅÅ-MM-DD")
    parser.add_argument("--exclude-track", action="append", default=[])
    parser.add_argument("--include-gallop", action="store_true")
    parser.add_argument("--json", help="skriv rapporten som JSON till denna fil")
    args = parser.parse_args()

    excluded = list(args.exclude_track)
    if not args.include_gallop:
        excluded.extend(settings.GALLOP_TRACKS)

    db = DatabaseManager()
    rows = db.observations_for_analysis()
    db.close()

    per_strategy, skipped = build_races(
        rows, settings.COVERAGE_STRATEGIES, excluded_tracks=excluded,
        since=args.since, until=args.until,
        distance_classes=settings.DISTANCE_CLASSES,
    )

    analyses = {s: miss_analysis(r) for s, r in per_strategy.items() if r}

    print(f"Läste {len(rows)} observationsrader.")
    print(format_miss_report(analyses, "alla lopp", skipped=skipped))

    path = args.json
    if path is None:
        os.makedirs("data/reports", exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = f"data/reports/misses_{stamp}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(analyses, f, ensure_ascii=False, indent=2)
    print(f"\nRapport sparad som JSON: {path}")


if __name__ == "__main__":
    main()
