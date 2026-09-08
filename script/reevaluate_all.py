"""
Kor om utvarderingen for ALLA tidigare utvarderade sparade system,
for att sakerstalla att statistiken ar korrekt efter de senaste
fixarna (platsfallback vid saknad finishOrder, reservsubstitution
vid strukna hastar, ratt scratched-falt).

Rapporterar vilka system som faktiskt fick ett andrat traff/miss-
utfall pa nagot lopp jamfort med den tidigare sparade
utvarderingen - sa du ser konkret vad fixarna paverkade, inte bara
att skriptet kordes.

Paverkar INTE outvarderade system (de som aldrig fatt en forsta
utvardering) - bara de som redan har en sparad "outcome".

Kor fran projektroten:
    python script/reevaluate_all.py
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.learning_engine import LearningEngine

PREDICTIONS_DIR = "data/races"

#
# Paus mellan varje utvardering, for att inte belasta ATG:s API
# med en snabb sekvens av manga anrop - samma princip som
# backfill_history.py.
#
REQUEST_DELAY_SECONDS = 1.5


def get_hit_fingerprint(outcome):
    #
    # En enkel {race_number: hit} - ordbok, for att jamfora fore
    # och efter omvarderingen utan att bry sig om ovriga falt
    # (vinnarnamn, reservbyte-detaljer osv).
    #
    if not outcome:
        return {}
    return {leg["race_number"]: leg.get("hit", False) for leg in outcome.get("legs", [])}


def main():
    if not os.path.isdir(PREDICTIONS_DIR):
        print(f"Hittar inte {PREDICTIONS_DIR}")
        return

    filenames = sorted(f for f in os.listdir(PREDICTIONS_DIR) if f.endswith(".json"))

    engine = LearningEngine()

    total = 0
    skipped_never_evaluated = 0
    errored = 0
    changed = []

    for filename in filenames:
        prediction_id = filename[:-5]
        path = os.path.join(PREDICTIONS_DIR, filename)

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[HOPPAR OVER] {prediction_id} - kunde inte lasa filen: {exc}")
            errored += 1
            continue

        old_outcome = data.get("outcome")
        if old_outcome is None:
            #
            # Aldrig utvarderat forut - inget att sakerstalla har,
            # rör den inte.
            #
            skipped_never_evaluated += 1
            continue

        old_fingerprint = get_hit_fingerprint(old_outcome)

        print(f"Utvarderar om: {prediction_id}")

        try:
            new_outcome = engine.evaluate(prediction_id)
        except Exception as exc:
            print(f"  FEL vid omvardering: {exc!r}")
            errored += 1
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        total += 1

        new_fingerprint = get_hit_fingerprint(new_outcome)

        if old_fingerprint != new_fingerprint:
            diffs = []
            for race_number in sorted(set(old_fingerprint) | set(new_fingerprint)):
                old_hit = old_fingerprint.get(race_number)
                new_hit = new_fingerprint.get(race_number)
                if old_hit != new_hit:
                    diffs.append(f"V{race_number}: {old_hit} -> {new_hit}")

            if diffs:
                changed.append((prediction_id, diffs))
                print(f"  ANDRAT: {', '.join(diffs)}")

        time.sleep(REQUEST_DELAY_SECONDS)

    print()
    print("=" * 60)
    print("Klart.")
    print("=" * 60)
    print(f"Omvarderade: {total}")
    print(f"Aldrig utvarderade forut (hoppade over): {skipped_never_evaluated}")
    print(f"Fel vid omvardering: {errored}")
    print(f"System med andrat traff/miss-utfall: {len(changed)}")

    if changed:
        print()
        print("Detaljer om vad som andrades:")
        for prediction_id, diffs in changed:
            print(f"  {prediction_id}")
            for diff in diffs:
                print(f"    {diff}")


if __name__ == "__main__":
    main()
