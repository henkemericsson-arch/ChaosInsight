import os
import sqlite3
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db import DB_PATH
from learning.trav import settings

conn = sqlite3.connect(DB_PATH)

starts = conn.execute(
    "SELECT game_id, race_number, date, track, odds, bet_percentage, "
    "actual_place, actual_finish_order, actual_scratched FROM backfill_starts"
).fetchall()

observed_games = {
    r[0] for r in conn.execute("SELECT DISTINCT game_id FROM observations")
}

legs = {}
for game, race, date, track, odds, streck, place, finish, scratched in starts:
    leg = legs.setdefault((game, race), {"date": date, "track": track, "horses": []})
    leg["horses"].append((odds, streck, place, finish, scratched))

usable = 0
usable_by_type = Counter()
usable_by_track = Counter()
dates = []
gallop = 0

for (game, race), leg in legs.items():
    active = [h for h in leg["horses"] if not h[4] and not (h[0] is not None and h[0] <= 0)]
    has_winner = any(h[2] == 1 or (h[2] is None and h[3] == 1) for h in active)
    has_odds = bool(active) and all(h[0] is not None and h[0] > 0 for h in active)
    has_streck = bool(active) and all(h[1] is not None for h in active)

    if not (has_winner and has_odds and has_streck):
        continue

    name = (leg["track"] or "").casefold()
    if any(t.casefold() in name for t in settings.GALLOP_TRACKS):
        gallop += 1
        continue

    usable += 1
    usable_by_type[str(game).split("_")[0]] += 1
    usable_by_track[leg["track"]] += 1
    if leg["date"]:
        dates.append(leg["date"])

games = {g for g, _ in legs}
print(f"Startrader i backfill_starts:      {len(starts)}")
print(f"Spel (game_id):                    {len(games)}")
print(f"Lopp totalt:                       {len(legs)}")
print(f"Lopp med vinnare + odds + streck:  {usable}  (galoppbana bortsorterad: {gallop})")
if dates:
    print(f"Datumspann (användbara lopp):      {min(dates)} .. {max(dates)}")
print(f"Spel som också finns i observationer (live-data): {len(games & observed_games)}")
print()
print("Användbara lopp per speltyp (game_id före första '_'):")
for key, count in usable_by_type.most_common(10):
    print(f"  {key:20} {count}")
print()
print("Användbara lopp per bana (topp 10):")
for key, count in usable_by_track.most_common(10):
    print(f"  {str(key):20} {count}")
