#
# Etapp 1 i Learning Engine: kalibreringsrapport.
# Körs från projektroten:  python script/learning_calibration_report.py
#
# Läser bara - ändrar ingenting i databasen eller systemet.
#
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foundation.database_manager import DatabaseManager
from learning.analysis.calibration import compute_calibration
from learning.analysis.calibration_report import format_report
from learning.observation_reader import build_races
from learning.trav import settings


def run_period(rows, title, since, until, excluded_tracks, min_segment):
    races_by_model, skipped = build_races(
        rows,
        settings.MODEL_STRATEGIES,
        excluded_tracks=excluded_tracks,
        since=since,
        until=until,
        distance_classes=settings.DISTANCE_CLASSES,
    )
    report = compute_calibration(races_by_model, min_segment_races=min_segment)
    text = format_report(
        report, title, settings.MIN_RACES_FOR_TUNING, skipped=skipped
    )
    return report, text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="första loppdatum, ÅÅÅÅ-MM-DD")
    parser.add_argument("--until", help="sista loppdatum, ÅÅÅÅ-MM-DD")
    parser.add_argument("--exclude-track", action="append", default=[],
                        help="extra bana att utesluta (kan anges flera gånger)")
    parser.add_argument("--include-gallop", action="store_true",
                        help="uteslut inte galoppbanorna i settings.GALLOP_TRACKS")
    parser.add_argument("--min-segment", type=int, default=5)
    parser.add_argument("--json", help="skriv rapporten som JSON till denna fil")
    args = parser.parse_args()

    excluded = list(args.exclude_track)
    if not args.include_gallop:
        excluded.extend(settings.GALLOP_TRACKS)

    db = DatabaseManager()
    rows = db.observations_for_analysis()
    db.close()

    print(f"Läste {len(rows)} observationsrader.")
    if excluded:
        print("Utesluter banor: " + ", ".join(excluded))

    results = {}
    texts = []

    if not settings.REGIMES:
        report, text = run_period(
            rows, "alla lopp", args.since, args.until, excluded, args.min_segment
        )
        results["alla lopp"] = report
        texts.append(text)
    else:
        for i, (name, start) in enumerate(settings.REGIMES):
            next_start = (
                settings.REGIMES[i + 1][1] if i + 1 < len(settings.REGIMES) else None
            )
            since = max(start, args.since) if args.since else start
            # until är exklusivt mot nästa regims start -> dagen före ersätts
            # av jämförelse "<" genom att skicka dagen före som sträng.
            until = args.until
            if next_start:
                prev_day = _day_before(next_start)
                until = min(until, prev_day) if until else prev_day
            report, text = run_period(
                rows, f"regim: {name} (från {start})", since, until, excluded,
                args.min_segment,
            )
            results[name] = report
            texts.append(text)

    print("\n\n".join(texts))

    path = args.json
    if path is None:
        os.makedirs("data/reports", exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = f"data/reports/calibration_{stamp}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nRapport sparad som JSON: {path}")


def _day_before(date_string):
    from datetime import date, timedelta
    return (date.fromisoformat(date_string) - timedelta(days=1)).isoformat()


if __name__ == "__main__":
    main()
