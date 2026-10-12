#
# Parameterlagret i Learning Engine: visar aktiv uppsättning och alla
# versioner. Skapar baseline (version 0) om den saknas. Ändrar inget annat.
# Körs från projektroten:  python script/learning_parameters.py
#
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foundation.database_manager import DatabaseManager
from learning.trav.parameter_schema import BASELINE
from learning.tuning.parameter_store import ParameterStore


def main():
    db = DatabaseManager()
    store = ParameterStore(db)
    store.ensure_baseline(BASELINE)

    active = store.active()
    print(f"Aktiv uppsättning: version {active['version']} ({active['status']})")
    print(f"  skapad {active['created_at']}  orsak: {active['reason']}")
    print()
    for name in sorted(active["params"]):
        base = BASELINE.get(name)
        value = active["params"][name]
        mark = "" if base == value else f"   (baseline {base})"
        print(f"  {name:<28} {value}{mark}")

    print()
    print("Alla versioner:")
    for row in store.all():
        parent = "-" if row["parent"] is None else row["parent"]
        print(f"  v{row['version']:<3} {row['status']:<12} förälder {parent!s:<4} {row['created_at']}  {row['reason']}")

    missing = sorted(set(BASELINE) - set(active["params"]))
    if missing:
        print()
        print("Saknas i aktiv uppsättning (baseline används):", ", ".join(missing))


if __name__ == "__main__":
    main()
