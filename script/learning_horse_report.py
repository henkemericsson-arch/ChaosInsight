#
# Hästnivå i Learning Engine: underskattas/överskattas vissa hästar
# återkommande av marknaden? Körs från projektroten:
#   python script/learning_horse_report.py
#
# Läser bara - ändrar ingenting. Strömmar historiken, så minnesåtgången
# är liten, men körningen kan ta några minuter på stor historik.
#
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foundation.database_manager import DatabaseManager
from learning.analysis.horse_residual import (
    fit_market,
    iter_prepared_legs,
    walk_forward,
)
from learning.analysis.horse_residual_report import format_horse_report
from learning.trav import settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prior", type=float, default=2.0,
                        help="prior (förväntade vinster) som drar kvoten mot 1")
    parser.add_argument("--min-starts", type=int, default=5,
                        help="minsta antal tidigare starter för att en häst ska räknas")
    parser.add_argument("--exclude-track", action="append", default=[])
    parser.add_argument("--include-gallop", action="store_true")
    parser.add_argument("--json", help="skriv rapporten som JSON till denna fil")
    args = parser.parse_args()

    excluded = list(args.exclude_track)
    if not args.include_gallop:
        excluded.extend(settings.GALLOP_TRACKS)

    def legs():
        db = DatabaseManager()
        try:
            yield from iter_prepared_legs(db.iter_backfill_legs(), excluded)
        finally:
            db.close()

    if excluded:
        print("Utesluter banor: " + ", ".join(excluded))

    print("Steg 1/2: kalibrerar marknaden ...")
    market = fit_market(legs())
    if not market["n_legs"]:
        print("Inga användbara lopp i historiken.")
        return
    print(f"  {market['n_legs']} lopp, k = {market['k']}")

    print("Steg 2/2: framåtriktat test per häst ...")
    walk = walk_forward(
        legs(), market["k"], prior=args.prior, min_starts=args.min_starts,
        progress=lambda n: print(f"  {n} lopp ..."),
    )

    print()
    print(format_horse_report(market, walk, "hela historiken"))

    path = args.json
    if path is None:
        os.makedirs("data/reports", exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = f"data/reports/horse_residual_{stamp}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump({"market": market, "walk_forward": walk}, f, ensure_ascii=False, indent=2)
    print(f"\nRapport sparad som JSON: {path}")


if __name__ == "__main__":
    main()
