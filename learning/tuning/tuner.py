#
# Tuner - flödet för automatisk justering (005 avsnitt 18).
# Generell: allt travspecifikt kommer från en adapter (learning/trav/
# tuning_adapter.py). Tuner läser lopp, bygger en kandidat, låter guard
# verifiera den och antar eller avvisar den. Ingen SQL här - parameter-
# uppsättningar via ParameterStore, tillstånd och logg via TuningLog.
#
# Adaptern ska ha:
#   baseline                dict med baseline-värden
#   adjustable              namn som får justeras individuellt
#   sum_groups              tupler av namn med konstant summa
#   load_races()            lopp i weight_analysis-formen (aktuell regim)
#   effective_weights(p)    lista med effektiv vikt per signal
#   propose(betas, p)       hel uppsättning (förslag) eller None
#

from learning.analysis.scoring_comparison import (
    compare_in_place, compare_scorings, split_by_time,
)
from learning.analysis.weight_analysis import fit_conditional_logit
from learning.tuning import adjuster, guard, rollback_monitor
from learning.tuning.parameter_store import BASELINE_VERSION


class Tuner:

    def __init__(self, store, log, adapter, settings):
        self._store = store
        self._log = log
        self._adapter = adapter
        self._cfg = settings

    # ------------------------------------------------------------
    # Hjälpare
    # ------------------------------------------------------------

    def _active(self):
        self._store.ensure_baseline(self._adapter.baseline)
        row = self._store.active()
        params = dict(self._adapter.baseline)
        params.update(row["params"])
        return row, params

    def _params_of(self, version):
        row = self._store.get(version)
        params = dict(self._adapter.baseline)
        if row is not None:
            params.update(row["params"])
        return params

    def _last_adopted_date(self):
        adopted = [
            r for r in self._store.all()
            if r["version"] != BASELINE_VERSION and r["status"] in ("active", "rolled_back")
        ]
        if not adopted:
            return None
        return max(r["created_at"] for r in adopted)[:10]

    # ------------------------------------------------------------
    # status
    # ------------------------------------------------------------

    def status(self):
        row, params = self._active()
        races = self._adapter.load_races()
        last = self._last_adopted_date()
        n_new = len(races) if last is None else sum(1 for r in races if (r["date"] or "") > last)
        changed = {
            name: (self._adapter.baseline[name], params[name])
            for name in self._adapter.baseline
            if abs(params[name] - self._adapter.baseline[name]) > 1e-12
        }
        return {
            "enabled": self._log.enabled(),
            "active_version": row["version"],
            "active_status": row["status"],
            "changed_from_baseline": changed,
            "n_races": len(races), "n_new": n_new, "last_adjustment_date": last,
            "min_races": self._cfg["min_races"], "min_new": self._cfg["min_new_races"],
            "recent": self._log.entries(5),
        }

    # ------------------------------------------------------------
    # run
    # ------------------------------------------------------------

    def run(self, dry_run=False):
        cfg, adapter = self._cfg, self._adapter

        if not dry_run and not self._log.enabled():
            return {"outcome": "disabled",
                    "reason": "Automatisk justering är avstängd (slå på med 'enable', eller prova med --dry-run)."}

        row, current = self._active()
        races = adapter.load_races()
        last = self._last_adopted_date()
        n_new = len(races) if last is None else sum(1 for r in races if (r["date"] or "") > last)

        checks = guard.check_data(len(races), n_new, cfg["min_races"], cfg["min_new_races"])
        if not guard.all_passed(checks):
            return {"outcome": "skipped", "reason": "underlaget räcker inte", "checks": checks,
                    "n_races": len(races), "n_new": n_new, "active_version": row["version"]}

        train, test = split_by_time(races)
        betas = fit_conditional_logit(train, ridge=cfg["ridge"])["beta"]
        proposal = adapter.propose(betas, current)
        if proposal is None:
            return {"outcome": "skipped", "reason": "inga positiva koefficienter – inget förslag",
                    "checks": checks, "n_races": len(races), "n_new": n_new,
                    "active_version": row["version"]}

        candidate = adjuster.build_candidate(
            current, proposal, adapter.baseline, cfg["damping"], cfg["step_cap"],
            cfg["total_cap"], adapter.adjustable, adapter.sum_groups,
        )

        now_weights = adapter.effective_weights(current)
        # Steget som skulle antas, och riktningen som data stödjer (hela förslaget).
        comparison = compare_scorings(train, test, now_weights, adapter.effective_weights(candidate))
        direction = compare_scorings(train, test, now_weights, adapter.effective_weights(proposal))

        names = list(adapter.adjustable) + [n for group in adapter.sum_groups for n in group]
        allowed = set(names)
        checks += [
            guard.check_signal(direction["delta_ci"]),
            guard.check_walk_forward(comparison["delta_mean"]),
            guard.check_damping(current, proposal, candidate, cfg["damping"],
                                adapter.adjustable, adapter.sum_groups),
            guard.check_caps(current, candidate, adapter.baseline,
                             cfg["step_cap"], cfg["total_cap"], names),
            guard.check_sums(current, candidate, adapter.sum_groups),
            guard.check_scope(current, candidate, allowed),
            guard.check_meaningful(current, candidate, names),
        ]
        passed = guard.all_passed(checks)

        changes = {
            n: [current[n], candidate[n]] for n in sorted(names)
            if abs(candidate[n] - current[n]) > 1e-12
        }
        evidence = {
            "n_races": len(races), "n_train": len(train), "n_test": len(test),
            "train_range": [train[0]["date"], train[-1]["date"]],
            "test_range": [test[0]["date"], test[-1]["date"]],
            "comparison": {k: comparison[k] for k in ("loss_a", "loss_b", "delta_mean", "delta_ci")},
            "direction": {k: direction[k] for k in ("loss_a", "loss_b", "delta_mean", "delta_ci")},
            "checks": checks, "changes": changes, "candidate": candidate,
        }

        report = {
            "outcome": None, "checks": checks, "changes": changes,
            "comparison": comparison, "direction": direction, "n_races": len(races), "n_new": n_new,
            "n_train": len(train), "n_test": len(test), "active_version": row["version"],
        }

        if passed:
            report["outcome"] = "would_adopt" if dry_run else "adopted"
            if not dry_run:
                reason = (f"Dämpad justering från version {row['version']}: riktningen slog nuvarande på "
                          f"{len(test)} osedda lopp (skillnad {direction['delta_mean']:+.4f}), "
                          f"steget {comparison['delta_mean']:+.4f}.")
                version = self._store.add(candidate, parent=row["version"], reason=reason,
                                          evidence=evidence, status="active")
                self._log.record("adopted", version, reason, evidence)
                report["version"] = version
        else:
            failed = [c["rule"] for c in checks if not c["ok"]]
            report["outcome"] = "would_reject" if dry_run else "rejected"
            if not dry_run:
                reason = "Kandidaten avvisades: " + "; ".join(failed)
                version = self._store.add(candidate, parent=row["version"], reason=reason,
                                          evidence=evidence, status="rejected")
                self._log.record("rejected", version, reason, evidence)
                report["version"] = version
        return report

    # ------------------------------------------------------------
    # monitor (återrullning)
    # ------------------------------------------------------------

    def monitor(self, dry_run=False):
        cfg, adapter = self._cfg, self._adapter
        row, current = self._active()
        version = row["version"]
        if version == BASELINE_VERSION:
            return {"decision": "nothing", "reason": "Baseline är aktiv – ingen justering att övervaka.",
                    "active_version": version}

        parent = row["parent"] if row["parent"] is not None else BASELINE_VERSION
        races = sorted(
            [r for r in adapter.load_races() if r.get("parameter_version") == version],
            key=lambda r: (r["date"] or "", str(r["key"])),
        )[: cfg["rollback_window"]]

        if len(races) < 2:
            verdict = rollback_monitor.decide(len(races), None, cfg["rollback_min_races"])
            return dict(verdict, n_races=len(races), active_version=version, parent=parent)

        comparison = compare_in_place(
            races,
            adapter.effective_weights(self._params_of(parent)),
            adapter.effective_weights(current),
        )
        verdict = rollback_monitor.decide(len(races), comparison["delta_ci"], cfg["rollback_min_races"])
        result = dict(verdict, n_races=len(races), active_version=version, parent=parent,
                      comparison=comparison)

        if verdict["decision"] == "rollback" and not dry_run:
            self._store.set_status(version, "rolled_back")
            self._log.record("rolled_back", version, verdict["reason"],
                             {"parent": parent, "comparison": comparison, "n_races": len(races)})
            result["rolled_back"] = True
        return result

    # ------------------------------------------------------------
    # reset / på- och avstängning
    # ------------------------------------------------------------

    def reset(self, to_version=BASELINE_VERSION):
        target = self._store.get(to_version)
        if to_version == BASELINE_VERSION and target is None:
            self._store.ensure_baseline(self._adapter.baseline)
            target = self._store.get(BASELINE_VERSION)
        if target is None:
            raise ValueError(f"Version {to_version} finns inte")

        replaced = []
        for r in self._store.all():
            if r["status"] == "active" and r["version"] > to_version:
                self._store.set_status(r["version"], "rolled_back")
                replaced.append(r["version"])
        if to_version != BASELINE_VERSION and target["status"] != "active":
            self._store.set_status(to_version, "active")

        reason = f"Manuell reset till version {to_version}; ersatta versioner: {replaced or 'inga'}."
        self._log.record("reset", to_version, reason, {"replaced": replaced})
        # En reset pausar automatiken tills användaren slår på den igen.
        self._log.set_enabled(False, "Automatisk justering pausad efter reset.")
        return {"active_version": to_version, "replaced": replaced, "enabled": False}

    def enable(self):
        self._log.set_enabled(True, "Slogs på manuellt.")

    def disable(self):
        self._log.set_enabled(False, "Stängdes av manuellt.")
