import math

from learning.metrics import normalize

#
# Hästnivå: underskattas/överskattas vissa hästar återkommande av
# marknaden? Mäter om en hästs tidigare avvikelse mellan faktiska
# vinster och marknadens förväntan förutsäger nästa start - strikt
# framåtriktat (hästens historik får bara innehålla äldre lopp).
#
# Läser bara - ändrar ingenting. Ingen SQL här: legs kommer som
# generator från DatabaseManager.
#
# Fallgropar som hanteras:
#   - Samma lopp kan finnas under flera spel (V75/V4/V5/V3 delar lopp).
#     Dubbletter tas bort via datum + hästuppsättning, annars dubbelräknas
#     historiken.
#   - Marknadens allmänna skevhet (långskott vinner färre än odds säger)
#     får inte tolkas som hästspecifik. Därför kalibreras marknaden först
#     (exponent k), och uppdelning görs per oddsband.
#   - Få starter ger extrema kvoter. Kvoten dras mot 1 med ett prior.
#

MARKET_K_GRID = [0.80 + 0.05 * i for i in range(13)]     # 0.80 .. 1.40
BETAS = (-0.5, 0.25, 0.5, 1.0, 2.0)
RATIO_EDGES = (0.6, 0.85, 1.15, 1.5)
BAND_EDGES = (0.08, 0.25)
BAND_LABELS = ("skräll-odds (<8 %)", "mellan (8-25 %)", "favorit (>25 %)")
ROLE_LABELS = ("favorit (rank 1)", "tvåa/trea i marknaden", "övriga")
SCOPES = ("all", "role")
BUCKET_LABELS = ("under 0,6", "0,6-0,85", "0,85-1,15", "1,15-1,5", "över 1,5")


def _is_winner(record):
    place = record.get("actual_place")
    if place is not None:
        return place == 1
    return record.get("actual_finish_order") == 1


def iter_prepared_legs(raw_legs, excluded_tracks=()):
    #
    # raw_legs: generator av (key, [startposter]) i kronologisk ordning.
    # Ger {date, names, p (marknad ur odds), win} per användbart lopp.
    # Hoppar över: uteslutna banor, lopp utan vinnare, lopp där något
    # aktivt hästs odds saknas, och dubbletter.
    #
    seen = set()
    excluded = tuple(t.casefold() for t in excluded_tracks)

    for (date, _game, _race), records in raw_legs:
        track = (records[0].get("track") or "").casefold()
        if any(t in track for t in excluded):
            continue

        active = [
            r for r in records
            if not r.get("actual_scratched")
            and not (r.get("odds") is not None and r["odds"] <= 0)
        ]
        if len(active) < 2 or any(r.get("odds") is None for r in active):
            continue
        if any(not r.get("horse_name") for r in active):
            continue
        if not any(_is_winner(r) for r in active):
            continue

        names = tuple(r["horse_name"] for r in active)
        signature = hash((date, tuple(sorted(names))))
        if signature in seen:
            continue
        seen.add(signature)

        yield {
            "date": date,
            "names": names,
            "p": normalize([1.0 / r["odds"] for r in active]),
            "win": [1 if _is_winner(r) else 0 for r in active],
        }


def _race_ll(probs, wins):
    losses = [-math.log(max(p, 1e-6)) for p, w in zip(probs, wins) if w]
    return sum(losses) / len(losses)


def _sharpen(probs, k):
    return normalize([p ** k for p in probs])


def _band(p):
    for i, edge in enumerate(BAND_EDGES):
        if p < edge:
            return i
    return len(BAND_EDGES)


def _roles(probs):
    #
    # Hästens roll i loppet enligt marknaden: 0 = favorit, 1 = tvåa eller
    # trea, 2 = övriga. Lika sannolikheter räknas som sämre rank.
    #
    roles = []
    for i, p in enumerate(probs):
        rank = 1 + sum(1 for j, q in enumerate(probs) if j != i and q >= p)
        roles.append(0 if rank == 1 else (1 if rank <= 3 else 2))
    return roles


def _bucket(ratio):
    for i, edge in enumerate(RATIO_EDGES):
        if ratio < edge:
            return i
    return len(RATIO_EDGES)


# ---------------------------------------------------------------------
# Pass 1: marknadens egen skevhet
# ---------------------------------------------------------------------

def fit_market(legs):
    #
    # Hittar exponenten k som kalibrerar marknadens sannolikheter bäst,
    # och mäter skevhet per oddsband (faktiska vinster / förväntade).
    #
    sums = {k: 0.0 for k in MARKET_K_GRID}
    n = 0
    bands = [{"E": 0.0, "W": 0.0, "V": 0.0, "n": 0} for _ in BAND_LABELS]

    for leg in legs:
        n += 1
        for k in MARKET_K_GRID:
            sums[k] += _race_ll(_sharpen(leg["p"], k), leg["win"])
        for p, w in zip(leg["p"], leg["win"]):
            b = bands[_band(p)]
            b["E"] += p
            b["W"] += w
            b["V"] += p * (1 - p)
            b["n"] += 1

    if not n:
        return {"n_legs": 0}

    best_k = min(sums, key=sums.get)
    return {
        "n_legs": n,
        "k": round(best_k, 2),
        "log_loss_by_k": {round(k, 2): s / n for k, s in sums.items()},
        "bands": [_band_summary(label, b) for label, b in zip(BAND_LABELS, bands)],
    }


def _band_summary(label, b):
    if not b["n"] or b["E"] <= 0:
        return {"label": label, "n": b["n"]}
    z = (b["W"] - b["E"]) / math.sqrt(b["V"]) if b["V"] > 0 else None
    return {
        "label": label,
        "n": b["n"],
        "expected": b["E"],
        "actual": b["W"],
        "ratio": b["W"] / b["E"],
        "z": z,
    }


# ---------------------------------------------------------------------
# Pass 2: hästens egen avvikelse mot marknaden, framåtriktat
# ---------------------------------------------------------------------

class HorseResidual:
    #
    # Håller per häst: vinster (W), marknadens förväntan (E) och antal
    # starter (N), eventuellt med avtagande vikt (decay < 1 ger nyare
    # starter större tyngd). ratio() = (W + prior) / (E + prior).
    #
    def __init__(self, decay, prior):
        self.decay = decay
        self.prior = prior
        self.W = {}
        self.E = {}
        self.N = {}

    def ratio(self, name):
        return (self.W.get(name, 0.0) + self.prior) / (self.E.get(name, 0.0) + self.prior)

    def starts(self, name):
        return self.N.get(name, 0)

    def update(self, name, win, p):
        self.W[name] = self.decay * self.W.get(name, 0.0) + win
        self.E[name] = self.decay * self.E.get(name, 0.0) + p
        self.N[name] = self.N.get(name, 0) + 1


def _new_tilt_stats():
    return {beta: {"n": 0, "sum": 0.0, "sumsq": 0.0} for beta in BETAS}


def _new_bucket_stats(n_groups):
    return [
        [{"n": 0, "E": 0.0, "W": 0.0, "V": 0.0} for _ in BUCKET_LABELS]
        for _ in range(n_groups)
    ]


def walk_forward(legs, k, decays=(1.0, 0.95), prior=2.0, min_starts=5,
                 progress=None):
    #
    # Varianter = avtagande vikt x omfång. Omfång "all": hästens hela
    # historik. Omfång "role": historiken räknas separat per roll i
    # loppet (favorit / tvåa-trea / övriga) och används bara när hästen
    # har samma roll nu - "favoriten som brukar missa", "trean som
    # brukar vinna".
    #
    variants = [(d, scope) for d in decays for scope in SCOPES]
    trackers = {v: HorseResidual(v[0], prior) for v in variants}
    #
    # Tilt-testet görs per grupp: omfång "all" = en grupp (alla hästar),
    # omfång "role" = en grupp per roll, så att en effekt som bara finns
    # för favoriter inte späds ut av brus från övriga roller.
    #
    tilt_groups = {v: ((None,) if v[1] == "all" else (0, 1, 2)) for v in variants}
    tilt = {v: {g: _new_tilt_stats() for g in tilt_groups[v]} for v in variants}
    buckets = {
        v: _new_bucket_stats(len(ROLE_LABELS) if v[1] == "role" else len(BAND_LABELS))
        for v in variants
    }
    n_legs = 0

    for leg in legs:
        n_legs += 1
        if progress and n_legs % 20000 == 0:
            progress(n_legs)

        base = _sharpen(leg["p"], k)
        base_ll = _race_ll(base, leg["win"])
        names = leg["names"]
        roles = _roles(base)

        for variant, tracker in trackers.items():
            scope = variant[1]
            keys = [(n, r) for n, r in zip(names, roles)] if scope == "role" else list(names)

            ratios = []
            for key in keys:
                if tracker.starts(key) >= min_starts:
                    ratios.append(tracker.ratio(key))
                else:
                    ratios.append(None)

            for group in tilt_groups[variant]:
                used = [
                    r if (r is not None and (group is None or roles[i] == group)) else None
                    for i, r in enumerate(ratios)
                ]
                if all(r is None for r in used):
                    continue

                logs = [math.log(r) if r is not None else 0.0 for r in used]
                for beta in BETAS:
                    tilted = normalize([p * math.exp(beta * lr) for p, lr in zip(base, logs)])
                    delta = _race_ll(tilted, leg["win"]) - base_ll
                    s_ = tilt[variant][group][beta]
                    s_["n"] += 1
                    s_["sum"] += delta
                    s_["sumsq"] += delta * delta

            for i, key in enumerate(keys):
                if ratios[i] is None:
                    continue
                group = roles[i] if scope == "role" else _band(base[i])
                cell = buckets[variant][group][_bucket(ratios[i])]
                cell["n"] += 1
                cell["E"] += base[i]
                cell["W"] += leg["win"][i]
                cell["V"] += base[i] * (1 - base[i])

        for variant, tracker in trackers.items():
            scope = variant[1]
            for i, (name, w, p) in enumerate(zip(names, leg["win"], base)):
                key = (name, roles[i]) if scope == "role" else name
                tracker.update(key, w, p)

    return {
        "n_legs": n_legs,
        "k": k,
        "prior": prior,
        "min_starts": min_starts,
        "variants": {
            f"{d}|{scope}": {
                "decay": d,
                "scope": scope,
                "tilt": {
                    ("alla" if g is None else ROLE_LABELS[g]): _summarize_tilt(stats)
                    for g, stats in tilt[(d, scope)].items()
                },
                "buckets": _summarize_buckets(
                    buckets[(d, scope)],
                    ROLE_LABELS if scope == "role" else BAND_LABELS,
                ),
            }
            for d, scope in variants
        },
    }


def _summarize_tilt(stats):
    rows = []
    for beta, s in stats.items():
        if s["n"] < 2:
            rows.append({"beta": beta, "n_legs": s["n"]})
            continue
        mean_delta = s["sum"] / s["n"]
        var = max(s["sumsq"] / s["n"] - mean_delta ** 2, 0.0)
        half = 1.96 * math.sqrt(var / s["n"])
        rows.append({
            "beta": beta,
            "n_legs": s["n"],
            "mean_delta_log_loss": mean_delta,
            "ci95": [mean_delta - half, mean_delta + half],
        })
    return rows


def _summarize_buckets(buckets, group_labels):
    rows = []
    for group_label, group in zip(group_labels, buckets):
        for bucket_label, cell in zip(BUCKET_LABELS, group):
            if not cell["n"]:
                continue
            summary = _band_summary(f"{group_label} / kvot {bucket_label}", cell)
            summary["band"] = group_label
            summary["bucket"] = bucket_label
            rows.append(summary)
    return rows
