from foundation.run_info import load_metrics
from learning.metrics import normalize

#
# Bygger analysbara lopp ur observationsrader (en rad per häst och
# utvärdering). Tar emot färdiga rader som dicts - ingen SQL här,
# databasen nås bara via DatabaseManager.
#
# Ett "lopp" här = ett avgjort lopp för en modell, med fältet av
# hästar, modellens sannolikhet per häst (Total Score normaliserad
# per lopp) och vem som vann.
#


#
# Kolumner som följer med varje häst för att kunna jämföra missade
# vinnare mot valda hästar (missanalysen).
#
FEATURE_COLUMNS = (
    "odds", "bet_percentage", "start_position", "driver_win_pct",
    "trainer_win_pct", "horse_win_pct", "career_earnings",
    "shoe_changed", "sulky_changed",
)


def _is_winner(row):
    place = row.get("actual_place")
    if place is not None:
        return place == 1
    return row.get("actual_finish_order") == 1


def _is_scratched(row):
    #
    # ATG anger odds 0.0 för strukna hästar. Äldre observationer kan
    # sakna korrekt actual_scratched-flagga (felet låg i hur
    # resultatet tolkades), så odds <= 0 räknas också som struken.
    #
    if row.get("actual_scratched"):
        return True
    odds = row.get("odds")
    return odds is not None and odds <= 0


def _track_excluded(track, excluded_tracks):
    name = (track or "").casefold()
    return any(t.casefold() in name for t in excluded_tracks)


def _distance_class(distance, classes):
    if distance is None:
        return "okänd"
    for name, upper in classes:
        if upper is None or distance <= upper:
            return name
    return "okänd"


def build_races(rows, model_strategies, excluded_tracks=(), since=None,
                until=None, distance_classes=()):
    #
    # Returnerar (races_by_model, skipped):
    #   races_by_model[modell][(game_id, race_id)] = {
    #       "meta": {...}, "horses": [{number, score, odds,
    #                                  bet_percentage, win}, ...]}
    #   skipped: räknare med orsak -> antal lopp som inte kunde användas.
    #
    # Dubbletter: efter Learning Engines rensning finns högst en
    # observationsomgång per (game_id, strategi, lopp). Hör flera
    # strategier till samma modell (continuous/legacy) används den
    # senast loggade omgången - hela omgången, aldrig en blandning,
    # så att inte gamla hästar (t.ex. senare strukna) smyger med.
    #
    strategy_to_model = {
        strategy: model
        for model, strategies in model_strategies.items()
        for strategy in strategies
    }

    skipped = {
        "utanför datumintervall": 0,
        "uteslutna banor": 0,
        "ej avgjort/ingen vinnare": 0,
        "saknar poäng för någon häst": 0,
    }

    batches = {}
    for row in rows:
        model = strategy_to_model.get(row.get("strategy"))
        if model is None:
            label = f"okänd strategi '{row.get('strategy')}'"
            skipped[label] = skipped.get(label, 0) + 1
            continue

        date = row.get("date") or ""
        if (since and date < since) or (until and date > until):
            skipped["utanför datumintervall"] += 1
            continue

        if _track_excluded(row.get("track"), excluded_tracks):
            skipped["uteslutna banor"] += 1
            continue

        key = (model, row.get("game_id"), row.get("race_id"))
        batch_id = row.get("logged_at")
        batches.setdefault(key, {}).setdefault(batch_id, []).append(row)

    races_by_model = {model: {} for model in model_strategies}

    for (model, game_id, race_id), by_batch in batches.items():
        latest = by_batch[max(by_batch, key=lambda b: b or "")]
        active = [r for r in latest if not _is_scratched(r)]

        if not any(_is_winner(r) for r in active):
            skipped["ej avgjort/ingen vinnare"] += 1
            continue

        scores = [r.get("predicted_total_score") for r in active]
        if normalize(scores) is None:
            skipped["saknar poäng för någon häst"] += 1
            continue

        first = active[0]
        races_by_model[model][(game_id, race_id)] = {
            "meta": {
                "game_id": game_id,
                "race_id": race_id,
                "date": first.get("date"),
                "track": first.get("track"),
                "distance": first.get("distance"),
                "distance_class": _distance_class(
                    first.get("distance"), distance_classes
                ),
                "start_method": first.get("start_method"),
                "kaosvarde": first.get("kaosvarde"),
                "code_version": first.get("code_version"),
                "parameter_version": first.get("parameter_version"),
            },
            "horses": [
                {
                    "number": r.get("horse_number"),
                    "score": r.get("predicted_total_score"),
                    "odds": r.get("odds"),
                    "bet_percentage": r.get("bet_percentage"),
                    "win": 1 if _is_winner(r) else 0,
                    "chosen": bool(r.get("chosen_by_system")),
                    "galloped": bool(r.get("actual_galloped")),
                    "disqualified": bool(r.get("actual_disqualified")),
                    "features": {
                        name: r.get(name) for name in FEATURE_COLUMNS
                    },
                    # Alla delmått prediktionen loggade (tom för äldre rader).
                    "metrics": load_metrics(r.get("metrics_json")),
                }
                for r in active
            ],
        }

    return races_by_model, skipped
