"""
Kollar om bana+distans-fallbacken (track_distance_baseline_seconds)
hade tillrackligt med data for en specifik bana/distans - anvands
for att avgora om ett hoppat-over lopp berodde pa att aven
fallbacken saknade data, eller om nagot annat hindrade den.

Kor fran projektroten:
    python script/check_track_distance_fallback.py <bana> <distans>

Exempel:
    python script/check_track_distance_fallback.py "Solänget" 1140
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from foundation.database_manager import get_default_manager
from analysis_engine.baseline import MIN_STARTS_FOR_TRACK_DISTANCE_FALLBACK


def main():
    if len(sys.argv) < 3:
        print('Anvandning: python script/check_track_distance_fallback.py "<bana>" <distans>')
        return

    track = sys.argv[1]
    distance = int(sys.argv[2])

    db = get_default_manager()
    average, n_starts = db.track_distance_average_km_time(track, distance)

    print(f"Bana: {track}, distans: {distance}m (±100m)")
    print(f"Underliggande starter hittade: {n_starts}")
    print(f"Tröskel för att lita på fallbacken: {MIN_STARTS_FOR_TRACK_DISTANCE_FALLBACK}")

    if average is None:
        print("Genomsnitt: ingen giltig data alls")
    else:
        print(f"Genomsnitt: {average} sekunder/km")

    if n_starts >= MIN_STARTS_FOR_TRACK_DISTANCE_FALLBACK:
        print("\n-> Fallbacken SKULLE ha räckt till (tröskeln nådd).")
    else:
        print(f"\n-> Fallbacken räckte INTE till ({n_starts} < {MIN_STARTS_FOR_TRACK_DISTANCE_FALLBACK}).")


if __name__ == "__main__":
    main()
