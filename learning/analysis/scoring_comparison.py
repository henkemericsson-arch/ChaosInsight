#
# Jämförelse av två viktuppsättningar på samma lopp (005 avsnitt 18).
# Delpoängen är oberoende av vikterna, så båda uppsättningarnas poäng
# räknas om från loggade delpoäng: poäng = Σ vikt_j · delpoäng_j.
# Generell kod - känner inte till trav.
#

from learning.analysis.weight_analysis import (
    TRAIN_SHARE, _race_nll, fit_temperature, sort_by_time,
)
from learning.metrics import bootstrap_mean_ci


def with_scores(races, weights):
    return [
        dict(r, scores=[sum(w * v for w, v in zip(weights, row)) for row in r["x"]])
        for r in races
    ]


def split_by_time(races, train_share=TRAIN_SHARE):
    ordered = sort_by_time(races)
    cut = int(len(ordered) * train_share)
    return ordered[:cut], ordered[cut:]


def _losses(races, tau):
    return [_race_nll([tau * s for s in r["scores"]], r["winner"]) for r in races]


def _summary(losses_a, losses_b, seed):
    deltas = [b - a for a, b in zip(losses_a, losses_b)]
    return {
        "n": len(deltas),
        "loss_a": sum(losses_a) / len(deltas),
        "loss_b": sum(losses_b) / len(deltas),
        "delta_mean": sum(deltas) / len(deltas),
        "delta_ci": bootstrap_mean_ci(deltas, seed=seed),
    }


def compare_scorings(train, test, weights_a, weights_b, seed=12345):
    #
    # Walk-forward: temperaturen för varje uppsättning anpassas på
    # träningsloppen och prövas på de nyare testloppen. delta = b − a i
    # log-loss per lopp (negativt = b bättre).
    #
    tau_a = fit_temperature(with_scores(train, weights_a))
    tau_b = fit_temperature(with_scores(train, weights_b))
    a = _losses(with_scores(test, weights_a), tau_a)
    b = _losses(with_scores(test, weights_b), tau_b)
    return _summary(a, b, seed)


def compare_in_place(races, weights_a, weights_b, seed=12345):
    #
    # Parvis jämförelse på samma lopp (används av återrullningsvakten, där
    # alla lopp redan är "nya"). Temperaturen anpassas på loppen själva
    # (en enda parameter per uppsättning).
    #
    sa, sb = with_scores(races, weights_a), with_scores(races, weights_b)
    a = _losses(sa, fit_temperature(sa))
    b = _losses(sb, fit_temperature(sb))
    return _summary(a, b, seed)
