import math

from learning.analysis.leg_analysis import by_odds
from learning.metrics import bootstrap_mean_ci, mean, winner_rank

#
# Etapp 3: Missanalys. Lär av de egna prediktionerna: vad gick rätt,
# vad gick fel och varför. Läser bara - ändrar ingenting.
#
# Utgår från vilka hästar systemet faktiskt valde per lopp (chosen) och
# klassar varje lopp som träff eller miss. Missar delas i orsaksklasser,
# och de missade vinnarna jämförs mot de hästar systemet valde i stället.
#

SKRALL_ODDS = 10.0

CLASS_FAVORITE_DROPPED = "Favoriten vann men valdes bort"
CLASS_SKRALL = "Skräll (vinnarens odds >= 10)"
CLASS_NEAR = "Knapp miss (modellrank strax utanför valda)"
CLASS_BLIND = "Blindfläck (mellanodds, lågt rankad av modellen)"
CLASS_UNKNOWN = "Övrigt (saknar odds)"

MISS_CLASSES = (
    CLASS_FAVORITE_DROPPED, CLASS_SKRALL, CLASS_NEAR, CLASS_BLIND, CLASS_UNKNOWN,
)

ODDS_BANDS = (
    ("under 3", 0.0, 3.0),
    ("3-6", 3.0, 6.0),
    ("6-10", 6.0, 10.0),
    ("10-20", 10.0, 20.0),
    ("20 och över", 20.0, float("inf")),
)

#
# Egenskaper som jämförs: (kolumn, visningsnamn, transform).
# Positiv skillnad = den missade vinnaren har högre värde än de valda.
#
FEATURES = (
    ("odds", "Odds (log)", lambda v: math.log(v) if v and v > 0 else None),
    ("bet_percentage", "Streckprocent", float),
    ("start_position", "Startspår", float),
    ("driver_win_pct", "Förarens vinst-%", float),
    ("trainer_win_pct", "Tränarens vinst-%", float),
    ("horse_win_pct", "Hästens vinst-%", float),
    ("career_earnings", "Prispengar (log)", lambda v: math.log1p(v) if v and v >= 0 else None),
    ("shoe_changed", "Skoändring", float),
    ("sulky_changed", "Sulkyändring", float),
)


def _num(value, transform):
    if value is None:
        return None
    try:
        return transform(value)
    except (TypeError, ValueError):
        return None


def _rank_of(horses, target):
    #
    # Hästens placering i modellens rangordning (1 = högst poäng).
    #
    scores = [h["score"] for h in horses]
    outcomes = [1 if h["number"] == target["number"] else 0 for h in horses]
    return winner_rank(scores, outcomes)


def classify_leg(race):
    #
    # None om loppet saknar sparade val. Annars en dict med utfall.
    #
    horses = race["horses"]
    chosen = [h for h in horses if h["chosen"]]
    winners = [h for h in horses if h["win"]]
    if not chosen or not winners:
        return None

    width = len(chosen)
    chosen_numbers = {h["number"] for h in chosen}
    hit = any(w["number"] in chosen_numbers for w in winners)

    result = {
        "hit": hit,
        "width": width,
        "kaos": race["meta"].get("kaosvarde"),
        "winner_odds": winners[0]["odds"],
        "chosen_galloped": any(h["galloped"] or h["disqualified"] for h in chosen),
    }

    if hit:
        result["kind"] = "spik" if width == 1 else ("lås" if width == 2 else "gardering")
        return result

    winner = winners[0]
    ranked = by_odds(horses)
    favorite_won = bool(ranked) and ranked[0]["win"] == 1
    odds = winner["odds"]

    if odds is None or odds <= 0:
        miss_class = CLASS_UNKNOWN
    elif favorite_won:
        miss_class = CLASS_FAVORITE_DROPPED
    elif odds >= SKRALL_ODDS:
        miss_class = CLASS_SKRALL
    elif _rank_of(horses, winner) <= width + 2:
        miss_class = CLASS_NEAR
    else:
        miss_class = CLASS_BLIND

    result["miss_class"] = miss_class
    result["winner_model_rank"] = _rank_of(horses, winner)
    return result


def _feature_deltas(race):
    #
    # Vinnaren minus medelvärdet av de valda hästarna som förlorade
    # (i ett missat lopp är det alla valda; i ett träffat lopp alla
    # valda utom vinnaren). Per egenskap, om båda sidor har värde.
    #
    horses = race["horses"]
    chosen = [h for h in horses if h["chosen"]]
    winners = [h for h in horses if h["win"]]
    if not chosen or not winners:
        return None, None

    winner = winners[0]
    hit = winner["chosen"]
    losers = [h for h in chosen if not h["win"]]
    if not losers:
        return hit, {}

    deltas = {}
    for column, _, transform in FEATURES:
        w_value = _num(winner["features"].get(column), transform)
        l_values = [
            v for v in (_num(h["features"].get(column), transform) for h in losers)
            if v is not None
        ]
        if w_value is None or not l_values:
            continue
        deltas[column] = w_value - sum(l_values) / len(l_values)

    return hit, deltas


def miss_analysis(races, groups=3):
    legs = []
    for race in races.values():
        info = classify_leg(race)
        if info is not None:
            legs.append(info)

    result = {"n_legs": len(legs)}
    if not legs:
        return result

    hits = [l for l in legs if l["hit"]]
    misses = [l for l in legs if not l["hit"]]

    result["n_hit"] = len(hits)
    result["n_miss"] = len(misses)
    result["hit_rate"] = len(hits) / len(legs)

    result["hit_kinds"] = {
        kind: sum(1 for l in hits if l["kind"] == kind)
        for kind in ("spik", "lås", "gardering")
    }

    result["miss_classes"] = [
        {
            "label": label,
            "n": sum(1 for l in misses if l["miss_class"] == label),
        }
        for label in MISS_CLASSES
    ]

    result["by_winner_odds"] = []
    for label, low, high in ODDS_BANDS:
        band = [
            l for l in legs
            if l["winner_odds"] is not None and low <= l["winner_odds"] < high
        ]
        if band:
            result["by_winner_odds"].append({
                "band": label,
                "n_legs": len(band),
                "hit_rate": mean(1 if l["hit"] else 0 for l in band),
            })

    with_kaos = sorted((l for l in legs if l["kaos"] is not None), key=lambda l: l["kaos"])
    result["by_kaos"] = []
    if len(with_kaos) >= groups * 3:
        size = len(with_kaos) / groups
        for g in range(groups):
            chunk = with_kaos[round(g * size): round((g + 1) * size)]
            result["by_kaos"].append({
                "kaos_min": chunk[0]["kaos"],
                "kaos_max": chunk[-1]["kaos"],
                "n_legs": len(chunk),
                "hit_rate": mean(1 if l["hit"] else 0 for l in chunk),
                "mean_width": mean(l["width"] for l in chunk),
            })

    result["misses_with_chosen_galloping"] = (
        mean(1 if l["chosen_galloped"] else 0 for l in misses) if misses else None
    )
    result["hits_with_chosen_galloping"] = (
        mean(1 if l["chosen_galloped"] else 0 for l in hits) if hits else None
    )

    miss_deltas = {column: [] for column, _, _ in FEATURES}
    hit_deltas = {column: [] for column, _, _ in FEATURES}
    for race in races.values():
        hit, deltas = _feature_deltas(race)
        if deltas is None:
            continue
        target = hit_deltas if hit else miss_deltas
        for column, value in deltas.items():
            target[column].append(value)

    result["features"] = []
    for column, label, _ in FEATURES:
        m, h = miss_deltas[column], hit_deltas[column]
        m_ci = bootstrap_mean_ci(m)
        h_ci = bootstrap_mean_ci(h)
        result["features"].append({
            "label": label,
            "n_miss": len(m),
            "delta_miss": mean(m),
            "ci_miss": list(m_ci) if m_ci else None,
            "n_hit": len(h),
            "delta_hit": mean(h),
            "ci_hit": list(h_ci) if h_ci else None,
        })

    return result
