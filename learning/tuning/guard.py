#
# Guard - kontrollerar en kandidat mot skyddsräckena i 005 avsnitt 5,
# oberoende av adjuster (som byggde den). Ren logik utan I/O.
#
# Varje kontroll returnerar {"rule": ..., "ok": bool, "detail": text}.
# En kandidat antas bara om alla är ok (all_passed).
#

TOLERANCE = 1e-9


def _check(rule, ok, detail):
    return {"rule": rule, "ok": bool(ok), "detail": detail}


def check_data(n_races, n_new, min_races, min_new):
    return [
        _check("1 Tillräckligt med data", n_races >= min_races,
               f"{n_races} lopp, kräver minst {min_races}"),
        _check("7 Avkylning (nya lopp sedan senaste justering)", n_new >= min_new,
               f"{n_new} nya lopp, kräver minst {min_new}"),
    ]


def check_signal(delta_ci):
    #
    # Skyddsräcke 3: förbättringen som data stödjer (det anpassade förslaget
    # mot nuvarande, på nyare lopp) måste vara större än bruset.
    #
    ok = delta_ci is not None and delta_ci[1] < 0
    detail = "saknar intervall" if delta_ci is None else (
        f"förslaget mot nuvarande på osedda lopp, skillnad i log-loss 95 % KI "
        f"[{delta_ci[0]:+.4f}, {delta_ci[1]:+.4f}] – måste ligga helt under 0"
    )
    return _check("3 Statistisk signal", ok, detail)


def check_walk_forward(delta_mean):
    #
    # Skyddsräcke 6: kandidaten (det dämpade och tak-begränsade steget) måste
    # slå nuvarande på nyare lopp den inte sett. Steget är litet, så kravet är
    # att den inte är sämre och faktiskt bättre i punktskattning – signifikans
    # krävs av riktningen (skyddsräcke 3), inte av varje litet steg.
    #
    ok = delta_mean is not None and delta_mean < 0
    detail = (
        f"kandidat − nuvarande i log-loss per lopp: {delta_mean:+.4f} – måste vara under 0"
        if delta_mean is not None else "saknas"
    )
    return _check("6 Walk-forward: kandidaten slår nuvarande på osedda lopp", ok, detail)


def check_damping(current, proposal, candidate, damping, adjustable, sum_groups=()):
    names = list(adjustable) + [first for first, _ in sum_groups]
    worst = None
    for name in names:
        allowed = damping * abs(proposal[name] - current[name]) + TOLERANCE
        moved = abs(candidate[name] - current[name])
        if moved > allowed:
            worst = (name, moved, allowed)
            break
    detail = "ingen parameter rör sig mer än η · avståndet till förslaget" if worst is None else (
        f"{worst[0]} rör sig {worst[1]:.4f} > tillåtet {worst[2]:.4f}"
    )
    return _check("4 Dämpning", worst is None, detail)


def check_caps(current, candidate, baseline, step_cap, total_cap, names):
    for name in names:
        old, new, base = current[name], candidate[name], baseline[name]
        if old and abs(new - old) > abs(old) * step_cap + TOLERANCE:
            return _check("5 Stegtak", False,
                          f"{name}: {old:.4f} → {new:.4f} är mer än ±{step_cap:.0%} per justering")
        # Redan utanför totalt tak (t.ex. efter manuell ändring): får bara röra sig mot taket.
        low, high = base * (1 - total_cap), base * (1 + total_cap)
        if not (low - TOLERANCE <= new <= high + TOLERANCE) and abs(new - base) > abs(old - base) + TOLERANCE:
            return _check("5 Totalt tak", False,
                          f"{name}: {new:.4f} ligger utanför ±{total_cap:.0%} från baseline {base:.4f}")
    return _check("5 Stegtak och totalt tak", True,
                  f"alla parametrar inom ±{step_cap:.0%} per steg och ±{total_cap:.0%} från baseline")


def check_sums(current, candidate, sum_groups):
    for group in sum_groups:
        before = sum(current[n] for n in group)
        after = sum(candidate[n] for n in group)
        if abs(before - after) > 1e-9:
            return _check("Summa", False, f"{'+'.join(group)}: {before:.6f} → {after:.6f}")
    return _check("Summa", True, "grupper med konstant summa behåller den")


def check_scope(current, candidate, allowed_names):
    changed = [n for n in candidate if n not in allowed_names and candidate[n] != current[n]]
    return _check("Avgränsning", not changed,
                  "inga andra parametrar ändras" if not changed else "ändrar även: " + ", ".join(changed))


def check_meaningful(current, candidate, names, min_relative=0.005):
    biggest = 0.0
    for name in names:
        if current[name]:
            biggest = max(biggest, abs(candidate[name] - current[name]) / abs(current[name]))
    return _check("Meningsfull ändring", biggest >= min_relative,
                  f"största relativa ändring {biggest:.2%} (kräver minst {min_relative:.1%})")


def all_passed(checks):
    return all(c["ok"] for c in checks)
