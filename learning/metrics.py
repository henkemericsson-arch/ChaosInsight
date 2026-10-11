import math
import random

#
# Rena matematiska mått. Ingen kunskap om trav, databas eller filer.
# Alla funktioner arbetar på listor av sannolikheter (ett lopp) och
# utfall (1 = vann, 0 = vann inte).
#

EPS = 1e-6


def normalize(values):
    #
    # Skalar om värden till sannolikheter som summerar till 1.
    # None om något värde saknas eller summan inte är positiv.
    #
    if any(v is None for v in values):
        return None

    clipped = [max(v, 0.0) for v in values]
    total = sum(clipped)

    if total <= 0:
        return None

    return [v / total for v in clipped]


def brier(probs, outcomes):
    return sum((p - y) ** 2 for p, y in zip(probs, outcomes)) / len(probs)


def race_log_loss(probs, outcomes):
    #
    # -log(sannolikhet för vinnaren). Vid flera vinnare (dött lopp)
    # används medelvärdet.
    #
    losses = [-math.log(max(p, EPS)) for p, y in zip(probs, outcomes) if y]
    if not losses:
        return None
    return sum(losses) / len(losses)


def winner_rank(probs, outcomes):
    #
    # Vinnarens placering i modellens rangordning (1 = modellens
    # favorit). Lika sannolikheter räknas till vinnarens nackdel
    # (konservativt). Vid flera vinnare används den bäst rankade.
    #
    ranks = []
    for i, y in enumerate(outcomes):
        if not y:
            continue
        better_or_equal = sum(
            1 for j, p in enumerate(probs) if j != i and p >= probs[i]
        )
        ranks.append(1 + better_or_equal)

    return min(ranks) if ranks else None


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def reliability(pairs, edges):
    #
    # pairs: lista av (förutsagd sannolikhet, utfall 0/1) per häst.
    # edges: stigande gränser, t.ex. [0, .05, .1, .2, .3, .5, 1.0001].
    # Returnerar en rad per intervall: antal, medelprognos, faktisk
    # vinstfrekvens.
    #
    rows = []
    for low, high in zip(edges[:-1], edges[1:]):
        inside = [(p, y) for p, y in pairs if low <= p < high]
        rows.append({
            "low": low,
            "high": min(high, 1.0),
            "n": len(inside),
            "mean_predicted": mean(p for p, _ in inside),
            "actual_rate": mean(y for _, y in inside),
        })
    return rows


def bootstrap_mean_ci(values, n_resamples=2000, seed=12345, level=0.95):
    #
    # Percentil-bootstrap av medelvärdet. Deterministisk (fast seed)
    # så att samma data alltid ger samma rapport.
    #
    values = list(values)
    if len(values) < 2:
        return None

    rng = random.Random(seed)
    size = len(values)
    means = []
    for _ in range(n_resamples):
        sample = [values[rng.randrange(size)] for _ in range(size)]
        means.append(sum(sample) / size)

    means.sort()
    tail = (1 - level) / 2
    low = means[int(tail * n_resamples)]
    high = means[min(int((1 - tail) * n_resamples), n_resamples - 1)]
    return low, high
