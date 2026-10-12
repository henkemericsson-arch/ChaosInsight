#
# Etapp 2a i Learning Engine: viktanalys (005 avsnitt 17).
# Körs från projektroten:  python script/learning_weight_report.py
#
# Läser bara - ändrar ingenting (inte heller parameterlagret).
#
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foundation.database_manager import DatabaseManager
from learning.analysis.weight_analysis import run_weight_analysis
from learning.analysis.weight_report import format_weight_report
from learning.observation_reader import build_races
from learning.trav import settings
from learning.trav.parameters import get_provider
from learning.trav.weight_features import (
    effective_weights, feature_names, param_names, to_parameters, to_weight_races,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="första loppdatum, ÅÅÅÅ-MM-DD")
    parser.add_argument("--until", help="sista loppdatum, ÅÅÅÅ-MM-DD")
    parser.add_argument("--exclude-track", action="append", default=[])
    parser.add_argument("--include-gallop", action="store_true")
    parser.add_argument("--parameter-version", type=int,
                        help="bara lopp gjorda med denna parameteruppsättning")
    parser.add_argument("--boot", type=int, default=settings.WEIGHT_BOOTSTRAP,
                        help="antal bootstrap-omtagningar för koefficienternas KI")
    parser.add_argument("--ridge", type=float, default=settings.WEIGHT_RIDGE)
    parser.add_argument("--json", help="skriv resultatet som JSON till denna fil")
    args = parser.parse_args()

    excluded = list(args.exclude_track)
    if not args.include_gallop:
        excluded.extend(settings.GALLOP_TRACKS)

    db = DatabaseManager()
    rows = db.observations_for_analysis()
    db.close()

    by_model, skipped = build_races(
        rows, {"kamt_v1": settings.MODEL_STRATEGIES["kamt_v1"]},
        excluded_tracks=excluded, since=args.since, until=args.until,
        distance_classes=settings.DISTANCE_CLASSES,
    )
    races = by_model["kamt_v1"]

    if args.parameter_version is not None:
        races = {
            key: race for key, race in races.items()
            if race["meta"].get("parameter_version") == args.parameter_version
        }

    weight_races, dropped, info = to_weight_races(races)

    provider = get_provider()
    provider.refresh()
    current = dict(provider.current().values)
    now = effective_weights(current)

    print(f"Läste {len(rows)} observationsrader, {len(races)} avgjorda KAMT v1-lopp.")
    print(f"Parameteruppsättning i drift: version {provider.version}")

    result = run_weight_analysis(
        weight_races, feature_names(), [now[p] for p in param_names()],
        propose=lambda betas: to_parameters(dict(zip(param_names(), betas)), current),
        min_report=settings.WEIGHT_MIN_RACES_REPORT,
        min_tuning=settings.MIN_RACES_FOR_TUNING,
        ridge=args.ridge, n_boot=args.boot,
    )

    meta = {"dropped": dropped, "info": info, "current_params": current}
    print(format_weight_report(result, meta))

    path = args.json
    if path is None:
        os.makedirs("data/reports", exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = f"data/reports/weights_{stamp}.json"

    serializable = dict(result)
    info_out = dict(info)
    info_out["versions"] = {str(k): v for k, v in info["versions"].items()}
    serializable["meta"] = {"dropped": dropped, "info": info_out}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nRapport sparad som JSON: {path}")


if __name__ == "__main__":
    main()
