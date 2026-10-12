#
# Travadapter för viktanalysen (005 avsnitt 17): vilka loggade mått som
# är signaler, hur de hör ihop med parametrarna i parameter_schema, och
# hur lopp byggs till den form som learning/analysis/weight_analysis.py
# förväntar sig. Den generella koden känner inget härifrån.
#

#
# (mått i metrics_json, parameternamn, visningsnamn)
# Ordningen är samma som i raderna i rapporten.
#
FEATURES = (
    ("crowd_odds_score", "crowd.odds", "Odds"),
    ("crowd_streck_score", "crowd.streck", "Streck"),
    ("crowd_trend_score", "crowd.trend", "Trend"),
    ("chaos_start_position_score", "chaos.start_position", "Startspår"),
    ("chaos_driver_form_score", "chaos.driver_form", "Kuskform"),
    ("chaos_horse_form_score", "chaos.horse_form", "Hästform"),
    ("chaos_trainer_form_score", "chaos.trainer_form", "Stallform"),
    ("chaos_distance_score", "chaos.distance", "Distans"),
    ("chaos_track_condition_score", "chaos.track_condition", "Underlag"),
    ("chaos_gallop_risk_score", "chaos.gallop_risk", "Galopprisk"),
    ("chaos_tempo_score", "chaos.tempo", "Tempo"),
)

#
# Trend saknas för hela loppet när ATG inte levererar den. CrowdEngine
# utelämnar då trend ur beräkningen; analysen ersätter med neutralt värde.
#
OPTIONAL_FEATURES = {"crowd_trend_score": 50.0}

EXPERT_METRICS = ("expert_index_obs", "expert_index")   # den som finns används

GROUP_SCORE_PARAM = {"crowd": "score.crowd", "chaos": "score.chaos"}

# Vilka crowd-parametrar som ingår i signalerna (expert prövas separat).
CROWD_PARAMS = ("crowd.odds", "crowd.streck", "crowd.trend")


def feature_names():
    return [name for _, _, name in FEATURES]


def param_names():
    return [param for _, param, _ in FEATURES]


# ----------------------------------------------------------------
# Lopp -> analysformat
# ----------------------------------------------------------------

def to_weight_races(races):
    #
    # `races`: dict (game_id, race_id) -> {"meta", "horses"} från
    # observation_reader.build_races. Returnerar (lopp, bortfall, info).
    #
    out = []
    dropped = {"saknar delpoäng (äldre lopp)": 0, "färre än 2 hästar": 0}
    imputed = 0
    versions = {}

    for key, race in races.items():
        horses = race["horses"]
        if len(horses) < 2:
            dropped["färre än 2 hästar"] += 1
            continue

        rows = []
        usable = True
        race_imputed = False
        for horse in horses:
            metrics = horse.get("metrics") or {}
            row = []
            for metric, _, _ in FEATURES:
                value = metrics.get(metric)
                if value is None:
                    if metric in OPTIONAL_FEATURES:
                        value = OPTIONAL_FEATURES[metric]
                        race_imputed = True
                    else:
                        usable = False
                        break
                row.append(float(value))
            if not usable:
                break
            rows.append(row)

        if not usable:
            dropped["saknar delpoäng (äldre lopp)"] += 1
            continue

        extra = []
        for horse in horses:
            metrics = horse.get("metrics") or {}
            value = next((metrics[m] for m in EXPERT_METRICS if metrics.get(m) is not None), None)
            extra.append(value)
        extra = [float(v) for v in extra] if all(v is not None for v in extra) else None

        winners = [i for i, h in enumerate(horses) if h.get("win")]
        if len(winners) != 1:
            continue

        meta = race["meta"]
        version = (meta.get("parameter_version"), meta.get("code_version"))
        versions[version] = versions.get(version, 0) + 1
        imputed += 1 if race_imputed else 0

        out.append({
            "key": key, "date": meta.get("date"),
            "x": rows, "scores": [float(h["score"]) for h in horses],
            "winner": winners[0], "extra": extra,
            "parameter_version": meta.get("parameter_version"),
        })

    return out, dropped, {"trend_imputed_races": imputed, "versions": versions}


# ----------------------------------------------------------------
# Koppling till parametrar
# ----------------------------------------------------------------

def _group_of(param):
    return param.split(".", 1)[0]


def effective_weights(params):
    #
    # Nuvarande effektiv vikt per signal i Total Score:
    #   score.<grupp> * vikt_j / summa(gruppens vikter)
    # Crowd räknas med trend och utan expert (expert prövas separat).
    #
    crowd_total = sum(params[p] for p in CROWD_PARAMS)
    chaos_params = [p for p in param_names() if _group_of(p) == "chaos"]
    chaos_total = sum(params[p] for p in chaos_params)

    weights = {}
    for param in param_names():
        if _group_of(param) == "crowd":
            weights[param] = params["score.crowd"] * params[param] / crowd_total
        else:
            weights[param] = params["score.chaos"] * params[param] / chaos_total
    return weights


def to_parameters(coefficients, current_params):
    #
    # Översätter koefficienter (param -> β) till ett förslag i
    # parametrarnas termer. Negativa β sätts till 0. Gruppernas
    # inbördes balans sätts av score.crowd/score.chaos; vikterna inom
    # gruppen blir proportionella mot β och behåller gruppens nuvarande
    # summa. Returnerar hela parameteruppsättningen, eller None om alla
    # koefficienter är <= 0.
    #
    positive = {p: max(coefficients[p], 0.0) for p in param_names()}
    totals = {
        "crowd": sum(positive[p] for p in CROWD_PARAMS),
        "chaos": sum(v for p, v in positive.items() if _group_of(p) == "chaos"),
    }
    grand = totals["crowd"] + totals["chaos"]
    if grand <= 0:
        return None

    proposal = dict(current_params)
    for group, score_param in GROUP_SCORE_PARAM.items():
        proposal[score_param] = totals[group] / grand
        if totals[group] <= 0:
            continue
        members = CROWD_PARAMS if group == "crowd" else [
            p for p in param_names() if _group_of(p) == "chaos"
        ]
        keep_sum = sum(current_params[p] for p in members)
        for p in members:
            proposal[p] = positive[p] / totals[group] * keep_sum
    return proposal
