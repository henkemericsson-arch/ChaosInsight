from learning.metrics import bootstrap_mean_ci, mean, normalize, winner_rank

#
# Etapp 1b: Spik/lås-urval, kaosvärde och täckning.
#
# Utgår från hur systemet faktiskt används: marknaden har nästan alltid
# en favorit per lopp, och spikar/lås bör spegla marknaden. Uppgiften är
# att välja VILKEN favorit (vilket lopp) som är säkrast att spika, och
# vilka lopp som ska låsas - enligt vår metod. Lopp utan klar favorit
# är lämpade för bred gardering.
#
# Därför mäts här:
#   1. Urval: bland ett spels lopp, hur ofta vinner favoriten i de lopp
#      som respektive kriterium rankar högst? (spikträff)
#   2. Kaosvärde: stämmer det att höga kaosvärden = svårare lopp?
#   3. Täckning: fanns vinnaren bland de hästar systemet valde, jämfört
#      med marknadens topp-N med exakt samma antal hästar?
#
# Allt läser bara - ändrar ingenting.
#

CRITERIA = {
    "ts_raw": "Total Score, råpoäng (som systemet använder)",
    "ts_share": "Total Score, andel av loppet",
    "mkt_odds": "Marknad: sannolikhet ur odds",
    "mkt_streck": "Marknad: streckandel",
    "low_kaos": "Lågt kaosvärde",
}

MARKET_REFERENCE = "mkt_odds"


# ---------------------------------------------------------------------
# Gemensamma hjälpare
# ---------------------------------------------------------------------

def _by_odds(horses):
    with_odds = [h for h in horses if h["odds"] is not None and h["odds"] > 0]
    return sorted(with_odds, key=lambda h: h["odds"])


def _implied_shares(horses):
    #
    # Marknadens sannolikheter ur odds, normaliserade över fältet.
    # None om något häst saknar giltigt odds.
    #
    if any(h["odds"] is None or h["odds"] <= 0 for h in horses):
        return None
    return dict(zip(
        (h["number"] for h in horses),
        normalize([1.0 / h["odds"] for h in horses]),
    ))


def _streck_shares(horses):
    values = [h["bet_percentage"] for h in horses]
    shares = normalize(values)
    if shares is None:
        return None
    return dict(zip((h["number"] for h in horses), shares))


def _score_shares(horses):
    shares = normalize([h["score"] for h in horses])
    if shares is None:
        return None
    return dict(zip((h["number"] for h in horses), shares))


# ---------------------------------------------------------------------
# 1. Urval av spik och lås
# ---------------------------------------------------------------------

def build_leg_records(races, kind):
    #
    # En post per lopp: vilka kriterievärden loppet har och om
    # favoriten (spik) respektive de två främsta favoriterna (lås)
    # vann. kind = "spike" eller "lock".
    #
    size = 1 if kind == "spike" else 2
    records = []

    for (game_id, race_id), race in races.items():
        horses = race["horses"]
        ranked = _by_odds(horses)
        if len(ranked) < size:
            continue

        picked = ranked[:size]
        picked_numbers = {h["number"] for h in picked}

        score_shares = _score_shares(horses)
        odds_shares = _implied_shares(horses)
        streck_shares = _streck_shares(horses)

        def total(getter):
            values = [getter(h) for h in picked]
            return None if any(v is None for v in values) else sum(values)

        kaos = race["meta"].get("kaosvarde")

        features = {
            "ts_raw": total(lambda h: h["score"]),
            "ts_share": total(lambda h: score_shares and score_shares[h["number"]]),
            "mkt_odds": total(lambda h: odds_shares and odds_shares[h["number"]]),
            "mkt_streck": total(lambda h: streck_shares and streck_shares[h["number"]]),
            "low_kaos": None if kaos is None else -kaos,
        }

        records.append({
            "game_id": game_id,
            "race_id": race_id,
            "outcome": 1 if any(
                h["win"] for h in horses if h["number"] in picked_numbers
            ) else 0,
            "features": features,
        })

    return records


def _games(records, min_legs):
    #
    # Grupperar lopp per spel; bara fullständiga lopp (alla kriterier
    # finns) och spel med minst min_legs sådana, så att alla kriterier
    # jämförs på exakt samma lopp.
    #
    complete = [
        r for r in records
        if all(v is not None for v in r["features"].values())
    ]
    by_game = {}
    for r in complete:
        by_game.setdefault(r["game_id"], []).append(r)

    return {g: legs for g, legs in sorted(by_game.items()) if len(legs) >= min_legs}


def hit_at(items, s):
    #
    # items: lista av (kriterievärde, utfall) för ett spels lopp.
    # Medelutfall i de s lopp som kriteriet rankar högst.
    #
    ranked = sorted(items, key=lambda it: it[0], reverse=True)
    top = ranked[:s]
    return sum(y for _, y in top) / len(top)


def within_game_auc(games_items):
    #
    # Sannolikheten att ett lopp där favoriten vann får högre kriterievärde
    # än ett lopp i SAMMA spel där den inte vann. 0,5 = slump.
    #
    wins = 0.0
    pairs = 0
    for items in games_items:
        positives = [c for c, y in items if y == 1]
        negatives = [c for c, y in items if y == 0]
        for p in positives:
            for n in negatives:
                pairs += 1
                wins += 1.0 if p > n else (0.5 if p == n else 0.0)
    return wins / pairs if pairs else None


def selection_analysis(races, kind, min_legs=4, max_s=3):
    records = build_leg_records(races, kind)
    games = _games(records, min_legs)

    result = {
        "kind": kind,
        "n_games": len(games),
        "n_legs": sum(len(g) for g in games.values()),
        "baseline": None,
        "criteria": {},
    }

    if not games:
        return result

    all_outcomes = [[r["outcome"] for r in legs] for legs in games.values()]
    result["baseline"] = mean(mean(o) for o in all_outcomes)

    per_game = {}
    for name in CRITERIA:
        items_per_game = [
            [(r["features"][name], r["outcome"]) for r in legs]
            for legs in games.values()
        ]
        per_game[name] = {
            s: [hit_at(items, min(s, len(items))) for items in items_per_game]
            for s in range(1, max_s + 1)
        }
        result["criteria"][name] = {
            "label": CRITERIA[name],
            **{f"hit{s}": mean(per_game[name][s]) for s in range(1, max_s + 1)},
            "auc": within_game_auc(items_per_game),
        }

    #
    # Jämförelse mot marknadsreferensen på spikträff@1, bootstrap över spel.
    #
    reference = per_game[MARKET_REFERENCE][1]
    for name in CRITERIA:
        if name == MARKET_REFERENCE:
            continue
        diffs = [a - b for a, b in zip(per_game[name][1], reference)]
        ci = bootstrap_mean_ci(diffs)
        result["criteria"][name]["delta1_vs_market"] = mean(diffs)
        result["criteria"][name]["delta1_ci95"] = list(ci) if ci else None

    return result


# ---------------------------------------------------------------------
# 2. Kaosvärde
# ---------------------------------------------------------------------

def kaos_analysis(races, groups=3):
    #
    # Delar lopp i lika stora grupper efter kaosvärde (lägst först) och
    # visar hur lätta de var att täcka. Om kaosvärdet säger något ska
    # höga kaosvärden ge lägre favoritträff och sämre täckning vid fast
    # bredd.
    #
    legs = []
    for race in races.values():
        kaos = race["meta"].get("kaosvarde")
        horses = race["horses"]
        ranked = _by_odds(horses)
        if kaos is None or len(ranked) < 3:
            continue

        by_score = sorted(horses, key=lambda h: h["score"], reverse=True)
        winners = {h["number"] for h in horses if h["win"]}

        legs.append({
            "kaos": kaos,
            "fav_win": 1 if ranked[0]["number"] in winners else 0,
            "mkt_top2": 1 if winners & {h["number"] for h in ranked[:2]} else 0,
            "mkt_top3": 1 if winners & {h["number"] for h in ranked[:3]} else 0,
            "mod_top3": 1 if winners & {h["number"] for h in by_score[:3]} else 0,
        })

    if len(legs) < groups * 3:
        return []

    legs.sort(key=lambda l: l["kaos"])
    size = len(legs) / groups
    rows = []
    for g in range(groups):
        chunk = legs[round(g * size): round((g + 1) * size)]
        rows.append({
            "kaos_min": chunk[0]["kaos"],
            "kaos_max": chunk[-1]["kaos"],
            "n_legs": len(chunk),
            "fav_win": mean(l["fav_win"] for l in chunk),
            "mkt_top2": mean(l["mkt_top2"] for l in chunk),
            "mkt_top3": mean(l["mkt_top3"] for l in chunk),
            "mod_top3": mean(l["mod_top3"] for l in chunk),
        })
    return rows


# ---------------------------------------------------------------------
# 3. Täckning
# ---------------------------------------------------------------------

def _width_label(width):
    return str(width) if width < 5 else "5+"


def coverage_analysis(races):
    #
    # races: {(game_id, race_id): race} för EN strategi. Täckning =
    # vinnaren fanns bland systemets valda hästar. Jämförs mot
    # marknadens topp-N (odds) där N = antal valda hästar i loppet.
    #
    skipped_no_choice = 0
    records = []

    for race in races.values():
        horses = race["horses"]
        chosen = {h["number"] for h in horses if h["chosen"]}
        if not chosen:
            skipped_no_choice += 1
            continue

        ranked = _by_odds(horses)
        if len(ranked) < len(chosen):
            continue

        market = {h["number"] for h in ranked[: len(chosen)]}
        winners = {h["number"] for h in horses if h["win"]}

        records.append({
            "width": len(chosen),
            "ours": 1 if winners & chosen else 0,
            "market": 1 if winners & market else 0,
            "same_set": chosen == market,
        })

    result = {
        "n_legs": len(records),
        "skipped_no_choice": skipped_no_choice,
    }
    if not records:
        return result

    result["mean_width"] = mean(r["width"] for r in records)
    result["ours"] = mean(r["ours"] for r in records)
    result["market"] = mean(r["market"] for r in records)

    diffs = [r["ours"] - r["market"] for r in records]
    ci = bootstrap_mean_ci(diffs)
    result["delta"] = mean(diffs)
    result["delta_ci95"] = list(ci) if ci else None

    by_width = {}
    for r in records:
        by_width.setdefault(_width_label(r["width"]), []).append(r)
    result["by_width"] = [
        {
            "width": label,
            "n_legs": len(items),
            "ours": mean(i["ours"] for i in items),
            "market": mean(i["market"] for i in items),
        }
        for label, items in sorted(by_width.items(), key=lambda kv: kv[0])
    ]

    differing = [r for r in records if not r["same_set"]]
    result["n_differing"] = len(differing)
    if differing:
        result["differing_ours"] = mean(r["ours"] for r in differing)
        result["differing_market"] = mean(r["market"] for r in differing)

    return result
