"""
Diagnostiserar varfor KAMT v2 tappade lopp/hastar for ett visst
spel - kollar hur manga giltiga historiska starter varje hast har,
och jamfor mot troskeln (MIN_STARTS_FOR_BASELINE) som avgor om en
hast far en egen baslinje overhuvudtaget.

Kor fran projektroten:
    python script/diagnose_baseline_coverage.py <game_id>

Exempel:
    python script/diagnose_baseline_coverage.py V64_2026-08-29_9_4
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.atg_client import ATGClient
from parsers.race_parser import RaceParser
from foundation.database_manager import get_default_manager
from analysis_engine.baseline import MIN_STARTS_FOR_BASELINE


def main():
    if len(sys.argv) < 2:
        print("Anvandning: python script/diagnose_baseline_coverage.py <game_id>")
        return

    game_id = sys.argv[1]

    client = ATGClient()
    raw_game_data = client.get_game(game_id)

    if not raw_game_data:
        print(f"Kunde inte hamta {game_id} fran ATG.")
        return

    race_parser = RaceParser()
    races = race_parser.parse(raw_game_data)

    db = get_default_manager()

    print(f"Diagnostik for {game_id} (troskel: {MIN_STARTS_FOR_BASELINE} giltiga starter)\n")

    for race in races:
        print(f"=== V{race.race_number} - {race.track} ({len(race.horses)} hastar, distans {race.distance}m) ===")

        horses_with_baseline = 0
        horses_without_baseline = 0

        for horse in race.horses:
            times = db.horse_km_times(horse.name, target_distance=race.distance, margin=100)
            has_baseline = len(times) >= MIN_STARTS_FOR_BASELINE
            marker = "OK" if has_baseline else "SAKNAS"

            if has_baseline:
                horses_with_baseline += 1
            else:
                horses_without_baseline += 1

            print(f"  {horse.number}. {horse.name:25s} {len(times)} giltiga starter  [{marker}]")

        print(f"  -> {horses_with_baseline} av {len(race.horses)} hastar har egen baslinje")
        if horses_with_baseline == 0:
            print(f"  -> DETTA LOPP KOMMER HOPPAS OVER HELT av KAMT v2 (ingen hast har data)")
        print()


if __name__ == "__main__":
    main()
