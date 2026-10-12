import argparse
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import expert_sources
from expert.collector import ExpertCollector, game_type
from expert.fetcher import Fetcher
from expert.interpreter import Interpreter
from expert.scoring import leg_index
from expert.text import extract_links
from expert.trav import lexicon
from foundation.database_manager import DatabaseManager
from models.game import Game
from services.analysis_data_collector import AnalysisDataCollector

#
# Samlar in experttips for ett spel och sparar dem i databasen.
#   python script/collect_expert_tips.py V85_2026-10-10_6_5
# Kan koras flera ganger (t.ex. fredag och lordag): ny hamtning ersatter
# kallans tidigare tips vid analysen, men aldrig i historiken.
#


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_id")
    parser.add_argument("--dry-run", action="store_true",
                        help="Tolka och visa, men spara inget")
    parser.add_argument("--show", action="store_true",
                        help="Visa expertindex per lopp (topp 5) for kontroll mot artiklarna")
    parser.add_argument("--debug-index", action="store_true",
                        help="Visa hur oversiktssidorna ser ut for artikelhittningen")
    args = parser.parse_args()

    game_id = args.game_id
    parts = game_id.split("_")
    game_date = parts[1] if len(parts) > 1 else None
    game = Game(game_id=game_id, name=game_type(game_id), track=None, date=game_date, races=0)

    try:
        analysis_data = AnalysisDataCollector().collect(game)
    except requests.HTTPError as exc:
        print(f"ATG hittar inget spel med id '{game_id}' ({exc.response.status_code}).")
        print("Anvand ett riktigt game_id, t.ex. filnamnet fore '__' i data/races/:")
        print("  ls data/races | sed 's/__.*//' | sort -u | tail")
        sys.exit(1)
    races = analysis_data.races
    roster = {
        leg: {horse.number: horse.name for horse in race.horses}
        for leg, race in enumerate(races, start=1)
    }
    track = races[0].track if races else None
    print(f"{game_id}: {len(races)} lopp, bana {track}")

    db = DatabaseManager()
    if args.dry_run:
        db.insert_expert_tip = lambda row, or_ignore=True: None
        db.insert_expert_article = lambda row, or_ignore=True: None

    collector = ExpertCollector(
        fetcher=Fetcher(),
        interpreter=Interpreter(lexicon),
        db=db,
        sources=expert_sources.SOURCES,
        manual_articles=expert_sources.MANUAL_ARTICLES,
    )
    if args.debug_index:
        fetcher = collector.fetcher
        gtype = game_type(game_id)
        for source in expert_sources.SOURCES:
            url = (source.get("index_urls") or {}).get(gtype)
            if not source.get("enabled") or not url:
                continue
            try:
                links = extract_links(fetcher.get_text(url))
            except Exception as exc:
                print(f"  {source['name']}: {exc!r}")
                continue
            print(f"  {source['name']}: {len(links)} lankar pa {url}")
            shown = [
                (h, t) for h, t in links
                if any(k in f"{h} {t}".lower() for k in ("v85", "v86", "gs75", "v64", "speltips", "tips"))
            ]
            for href, text in shown[:15]:
                print(f"      {text[:50]!r} -> {href[:90]}")
        print()

    reports = collector.collect(game_id, game_date, track, roster)

    print()
    for report in reports:
        status = report.get("status")
        if status == "ok":
            print(
                f"  {report['source']:<15} ok   lopp med tips {report['legs_with_tips']}/"
                f"{report['legs_in_roster']}  poster {report['tips']}  "
                f"otolkade ledtradar {report['unlinked_cues']}\n    {report['url']}"
            )
        else:
            print(f"  {report['source']:<15} {status}  {report.get('detail', '')}  {report.get('url', '')}")
    if args.show:
        weights = {s["name"]: s.get("weight", 1.0) for s in expert_sources.SOURCES}
        for leg, horses in roster.items():
            index = leg_index(
                [t for t in collector.last_tips if t.leg == leg],
                list(horses), lexicon.SIGNAL_WEIGHTS, lexicon.SUPPORT_CAP, weights,
            )
            top = sorted(index.items(), key=lambda kv: -kv[1])[:5]
            print(f"  Lopp {leg}: " + ", ".join(f"{n} {horses[n]} ({v:g})" for n, v in top))
    db.close()


if __name__ == "__main__":
    main()
