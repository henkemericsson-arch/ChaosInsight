from datetime import date as _date

from learning.metrics import (
    bootstrap_mean_ci,
    brier,
    mean,
    normalize,
    race_log_loss,
    reliability,
    winner_rank,
)

#
# Etapp 1: Kalibrering. Mäter hur väl modellernas sannolikheter
# stämmer mot verkligheten, och jämför dem mot marknaden (odds och
# streck) som referens. Läser bara - ändrar ingenting.
#
# Allt räknas på hästnivå (sannolikhet per häst mot vinnare), inte på
# om hela systemet fick rätt. Det är mycket mindre känsligt för hur
# garderingen byggdes, och ger många fler observationer än "antal
# 8-rätt".
#

MARKET_ODDS = "market_odds"
MARKET_STRECK = "market_streck"

SHARPNESS_GRID = [0.3 * (100 ** (i / 119)) for i in range(120)]   # 0.3 .. 30, logaritmiskt

RELIABILITY_EDGES = [0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 1.0001]


def merge_races(races_by_model):
    #
    # Slår ihop modellernas lopp per (game_id, race_id) till en
    # post med en sannolikhetslista per prediktor, alla i samma
    # hästordning. En modell vars startfält avviker från det första
    # (t.ex. olika strykningar vid olika tidpunkter) räknas inte med
    # för just det loppet.
    #
    merged = {}
    conflicts = 0

    for model, races in races_by_model.items():
        for key, race in races.items():
            horses = race["horses"]
            numbers = [h["number"] for h in horses]

            entry = merged.get(key)
            if entry is None:
                odds = [h["odds"] for h in horses]
                streck = [h["bet_percentage"] for h in horses]

                market_odds = None
                if all(o is not None and o > 0 for o in odds):
                    market_odds = normalize([1.0 / o for o in odds])

                entry = {
                    "meta": race["meta"],
                    "numbers": numbers,
                    "win": [h["win"] for h in horses],
                    "probs": {
                        MARKET_ODDS: market_odds,
                        MARKET_STRECK: normalize(streck),
                    },
                }
                merged[key] = entry

            if set(numbers) != set(entry["numbers"]):
                conflicts += 1
                entry["probs"][model] = None
                continue

            score_by_number = {h["number"]: h["score"] for h in horses}
            entry["probs"][model] = normalize(
                [score_by_number[n] for n in entry["numbers"]]
            )

    return merged, conflicts


def _sharpen(probs, k):
    return normalize([p ** k for p in probs])


def fit_sharpness(merged, predictor):
    #
    # Total Score är inget sannolikhetsmått, så "andel av summan" blir
    # ofta för platt (eller för spetsig). Det straffar log-loss även när
    # rangordningen är bra. Här hittas den exponent k som gör
    # p_i^k / summa(p^k) bäst kalibrerad (lägst log-loss). En enda
    # parameter per prediktor - försumbar överanpassning, men siffran
    # är ändå anpassad på samma lopp som den mäts på.
    #
    data = [
        (e["probs"][predictor], e["win"])
        for e in merged.values()
        if e["probs"].get(predictor) is not None
    ]
    if len(data) < 10:
        return None

    best_k, best_loss = None, None
    for k in SHARPNESS_GRID:
        loss = mean(race_log_loss(_sharpen(p, k), w) for p, w in data)
        if best_loss is None or loss < best_loss:
            best_k, best_loss = k, loss
    return round(best_k, 2)


def add_calibrated_probs(merged, predictors):
    #
    # Lägger till e["probs_cal"][predictor] = skärpejusterade
    # sannolikheter, och returnerar {predictor: k}.
    #
    sharpness = {}
    for predictor in predictors:
        k = fit_sharpness(merged, predictor)
        sharpness[predictor] = k
        for e in merged.values():
            p = e["probs"].get(predictor)
            cal = e.setdefault("probs_cal", {})
            cal[predictor] = _sharpen(p, k) if (p is not None and k) else None
    return sharpness


def summarize(merged, predictor, key="probs"):
    probs_win = [
        (e[key].get(predictor), e["win"])
        for e in merged.values()
        if e[key].get(predictor) is not None
    ]

    if not probs_win:
        return {"n_races": 0}

    ranks = [winner_rank(p, w) for p, w in probs_win]

    return {
        "n_races": len(probs_win),
        "n_horses": sum(len(p) for p, _ in probs_win),
        "brier": mean(brier(p, w) for p, w in probs_win),
        "log_loss": mean(race_log_loss(p, w) for p, w in probs_win),
        "top1": mean(1 if r == 1 else 0 for r in ranks),
        "top2": mean(1 if r <= 2 else 0 for r in ranks),
        "top3": mean(1 if r <= 3 else 0 for r in ranks),
        "mean_winner_probability": mean(
            sum(pi for pi, yi in zip(p, w) if yi) / sum(w)
            for p, w in probs_win
        ),
        "winner_rank_distribution": _rank_distribution(ranks),
    }


def _rank_distribution(ranks):
    counts = {}
    for r in ranks:
        label = str(r) if r <= 5 else "6+"
        counts[label] = counts.get(label, 0) + 1
    return counts


def reliability_table(merged, predictor, key="probs"):
    pairs = []
    for e in merged.values():
        p = e[key].get(predictor)
        if p is None:
            continue
        pairs.extend(zip(p, e["win"]))

    return reliability(pairs, RELIABILITY_EDGES)


def compare(merged, a, b, key="probs", min_races_for_verdict=30):
    #
    # Parvis jämförelse på exakt samma lopp. delta = log-loss(a) -
    # log-loss(b); negativt = a bättre än b.
    #
    deltas = []
    top1_a = []
    top1_b = []
    for e in merged.values():
        pa = e[key].get(a)
        pb = e[key].get(b)
        if pa is None or pb is None:
            continue
        deltas.append(race_log_loss(pa, e["win"]) - race_log_loss(pb, e["win"]))
        top1_a.append(1 if winner_rank(pa, e["win"]) == 1 else 0)
        top1_b.append(1 if winner_rank(pb, e["win"]) == 1 else 0)

    result = {
        "a": a, "b": b, "n_races": len(deltas),
        "top1_a": mean(top1_a), "top1_b": mean(top1_b),
    }

    if len(deltas) < 2:
        result["verdict"] = "för få gemensamma lopp"
        return result

    result["mean_delta_log_loss"] = mean(deltas)
    ci = bootstrap_mean_ci(deltas)
    result["ci95"] = list(ci)

    if len(deltas) < min_races_for_verdict:
        result["verdict"] = "för få lopp för slutsats"
    elif ci[1] < 0:
        result["verdict"] = f"{a} bättre än {b}"
    elif ci[0] > 0:
        result["verdict"] = f"{a} sämre än {b}"
    else:
        result["verdict"] = "ingen säker skillnad"

    return result


def segment_table(merged, predictor, min_races):
    #
    # Modellen mot marknadsodds uppdelat på bana, distansklass och
    # startmetod. Bara segment med minst min_races lopp visas -
    # mindre segment är brus.
    #
    rows = []

    for dimension in ("track", "distance_class", "start_method"):
        groups = {}
        for e in merged.values():
            p = e["probs_cal"].get(predictor)
            m = e["probs_cal"].get(MARKET_ODDS)
            if p is None or m is None:
                continue
            groups.setdefault(e["meta"].get(dimension) or "okänd", []).append(
                (p, m, e["win"])
            )

        for value, items in sorted(groups.items()):
            if len(items) < min_races:
                continue
            rows.append({
                "dimension": dimension,
                "value": value,
                "n_races": len(items),
                "top1_model": mean(
                    1 if winner_rank(p, w) == 1 else 0 for p, _, w in items
                ),
                "top1_market": mean(
                    1 if winner_rank(m, w) == 1 else 0 for _, m, w in items
                ),
                "log_loss_model": mean(race_log_loss(p, w) for p, _, w in items),
                "log_loss_market": mean(race_log_loss(m, w) for _, m, w in items),
            })

    return rows


def period_table(merged, predictor, min_races=5):
    #
    # Utveckling över tid (ISO-vecka) för att se om en modell blivit
    # bättre eller sämre, t.ex. efter större ändringar. Jämförs mot
    # marknadsodds på samma lopp, efter skärpejustering.
    #
    weeks = {}
    for e in merged.values():
        p = e["probs_cal"].get(predictor)
        m = e["probs_cal"].get(MARKET_ODDS)
        raw_date = e["meta"].get("date")
        if p is None or m is None or not raw_date:
            continue
        try:
            iso = _date.fromisoformat(raw_date[:10]).isocalendar()
        except ValueError:
            continue
        weeks.setdefault(f"{iso[0]}-v{iso[1]:02d}", []).append((p, m, e["win"]))

    rows = []
    for label, items in sorted(weeks.items()):
        if len(items) < min_races:
            continue
        rows.append({
            "period": label,
            "n_races": len(items),
            "top1_model": mean(1 if winner_rank(p, w) == 1 else 0 for p, _, w in items),
            "top1_market": mean(1 if winner_rank(m, w) == 1 else 0 for _, m, w in items),
            "delta_log_loss": mean(
                race_log_loss(p, w) - race_log_loss(m, w) for p, m, w in items
            ),
        })
    return rows


def compute_calibration(races_by_model, min_segment_races=5):
    merged, conflicts = merge_races(races_by_model)
    models = [m for m, races in races_by_model.items() if races]
    predictors = models + [MARKET_ODDS, MARKET_STRECK]

    pair_specs = []
    for m in models:
        pair_specs.append((m, MARKET_ODDS))
        pair_specs.append((m, MARKET_STRECK))
    if len(models) >= 2:
        pair_specs.append((models[0], models[1]))

    sharpness = add_calibrated_probs(merged, predictors)

    calibrated_pairs = [
        (a, b) for a, b in pair_specs if a in models
    ]

    return {
        "n_races_total": len(merged),
        "sharpness": sharpness,
        "summary_calibrated": {
            p: summarize(merged, p, key="probs_cal") for p in predictors
        },
        "comparisons_calibrated": [
            compare(merged, a, b, key="probs_cal") for a, b in calibrated_pairs
        ],
        "periods": {m: period_table(merged, m) for m in models},
        "reliability_calibrated": {
            p: reliability_table(merged, p, key="probs_cal") for p in models
        },
        "field_conflicts": conflicts,
        "models": models,
        "summary": {p: summarize(merged, p) for p in predictors},
        "reliability": {
            p: reliability_table(merged, p) for p in models + [MARKET_ODDS]
        },
        "comparisons": [compare(merged, a, b) for a, b in pair_specs],
        "segments": {m: segment_table(merged, m, min_segment_races) for m in models},
    }
