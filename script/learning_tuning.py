#
# Etapp 4 i Learning Engine: automatisk justering med skyddsräcken
# (005 avsnitt 18). Körs från projektroten:
#
#   python script/learning_tuning.py status
#   python script/learning_tuning.py run [--dry-run]
#   python script/learning_tuning.py monitor [--dry-run]
#   python script/learning_tuning.py enable | disable
#   python script/learning_tuning.py reset [--to VERSION]
#   python script/learning_tuning.py log [--limit N]
#
# Levereras AVSTÄNGD. 'run' ändrar inget förrän 'enable' har körts (eller
# med --dry-run, som aldrig skriver något).
#
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foundation.database_manager import DatabaseManager
from learning.trav.tuning_adapter import TravTuningAdapter, tuning_settings
from learning.tuning.parameter_store import ParameterStore
from learning.tuning.tuner import Tuner
from learning.tuning.tuning_log import TuningLog


def build_tuner():
    db = DatabaseManager()
    adapter = TravTuningAdapter(db.observations_for_analysis)
    return Tuner(ParameterStore(db), TuningLog(db), adapter, tuning_settings()), db


def _ver(version):
    return "v-" if version is None else f"v{version}"


def print_checks(checks):
    for c in checks:
        mark = "OK " if c["ok"] else "NEJ"
        print(f"  [{mark}] {c['rule']}: {c['detail']}")


def print_changes(changes):
    if not changes:
        print("  (inga ändringar)")
        return
    for name, (old, new) in changes.items():
        rel = (new - old) / old if old else 0.0
        print(f"  {name:<24} {old:>9.4f} -> {new:>9.4f}  ({rel:+.1%})")


def cmd_status(tuner, args):
    s = tuner.status()
    print(f"Automatisk justering: {'PÅ' if s['enabled'] else 'AV'}")
    print(f"Aktiv uppsättning: version {s['active_version']} ({s['active_status']})")
    print(f"Lopp i aktuell regim med delpoäng: {s['n_races']} (krav {s['min_races']})")
    since = s["last_adjustment_date"] or "ingen justering gjord"
    print(f"Nya lopp sedan senaste justering ({since}): {s['n_new']} (krav {s['min_new']})")
    if s["changed_from_baseline"]:
        print("Skillnader mot baseline:")
        print_changes({k: list(v) for k, v in s["changed_from_baseline"].items()})
    else:
        print("Vikterna är lika med baseline.")
    if s["recent"]:
        print("Senaste beslut:")
        for e in s["recent"]:
            print(f"  {e['logged_at'][:19]}  {e['action']:<11} {_ver(e['version'])}  {e['reason']}")


def cmd_run(tuner, args):
    r = tuner.run(dry_run=args.dry_run)
    prefix = "(torrkörning) " if args.dry_run else ""
    print(f"{prefix}Utfall: {r['outcome']}")
    if r.get("reason"):
        print(f"  {r['reason']}")
    if r.get("checks"):
        print("Skyddsräcken:")
        print_checks(r["checks"])
    for label, key in (("Riktningen (hela förslaget)", "direction"), ("Steget (kandidaten)", "comparison")):
        c = r.get(key)
        if c:
            ci = c["delta_ci"]
            print(f"{label} på {r['n_test']} osedda lopp: nuvarande {c['loss_a']:.4f}, ny {c['loss_b']:.4f}, "
                  f"skillnad {c['delta_mean']:+.4f} KI {'–' if ci is None else f'[{ci[0]:+.4f}, {ci[1]:+.4f}]'}")
    if "changes" in r:
        print("Föreslagna ändringar:")
        print_changes(r["changes"])
    if r.get("version") is not None:
        print(f"Sparad som version {r['version']}.")


def cmd_monitor(tuner, args):
    r = tuner.monitor(dry_run=args.dry_run)
    print(f"Beslut: {r['decision']} – {r['reason']}")
    if r.get("comparison"):
        c = r["comparison"]
        ci = c["delta_ci"]
        print(f"{r['n_races']} lopp med version {r['active_version']}: föräldern v{r['parent']} {c['loss_a']:.4f}, "
              f"aktiv {c['loss_b']:.4f}, skillnad {c['delta_mean']:+.4f} "
              f"KI {'–' if ci is None else f'[{ci[0]:+.4f}, {ci[1]:+.4f}]'}")
    if r.get("rolled_back"):
        print("Återrullad: föräldern är åter aktiv.")


def cmd_enable(tuner, args):
    tuner.enable()
    print("Automatisk justering är PÅ. 'run' kan nu ändra vikterna om alla skyddsräcken uppfylls.")
    print("Stäng av med: python script/learning_tuning.py disable")


def cmd_disable(tuner, args):
    tuner.disable()
    print("Automatisk justering är AV.")


def cmd_reset(tuner, args):
    r = tuner.reset(args.to)
    print(f"Återställt: version {r['active_version']} är aktiv. Ersatta versioner: {r['replaced'] or 'inga'}.")
    print("Automatisk justering är nu AV (slå på med 'enable').")


def cmd_log(tuner, args):
    entries = tuner._log.entries(args.limit)
    if not entries:
        print("Loggen är tom.")
    for e in entries:
        print(f"{e['logged_at'][:19]}  {e['action']:<11} {_ver(e['version'])}  {e['reason']}")


def main():
    parser = argparse.ArgumentParser(description="Automatisk justering (etapp 4)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    for name in ("run", "monitor"):
        p = sub.add_parser(name)
        p.add_argument("--dry-run", action="store_true", help="visa vad som skulle hända, skriv inget")
    sub.add_parser("enable")
    sub.add_parser("disable")
    p = sub.add_parser("reset")
    p.add_argument("--to", type=int, default=0, help="version att återgå till (förval 0 = baseline)")
    p = sub.add_parser("log")
    p.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    tuner, db = build_tuner()
    try:
        {"status": cmd_status, "run": cmd_run, "monitor": cmd_monitor, "enable": cmd_enable,
         "disable": cmd_disable, "reset": cmd_reset, "log": cmd_log}[args.command](tuner, args)
    finally:
        db.close()


if __name__ == "__main__":
    main()
