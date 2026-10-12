#
# Etapp 2a: viktanalys (005_Learning_Engine_Design.md avsnitt 17).
#
# Generell kärna - känner inte till trav. Den arbetar på "lopp" i
# följande form (adapterlagret bygger dem, se learning/trav/weight_features.py):
#
#   {
#     "key":    (game_id, race_id),     # identitet
#     "date":   "ÅÅÅÅ-MM-DD",           # för tidsordning
#     "x":      [[...], ...],           # signaler per häst (k st)
#     "scores": [...],                  # nuvarande modells poäng per häst
#     "winner": 3,                      # index (i listan) för vinnaren
#     "extra":  [...] eller None,       # kandidatsignal per häst (t.ex. expert)
#   }
#
# Modell: conditional logit. P(häst i vinner) = softmax(β·x)_i över loppet.
# Ren Python (inga externa bibliotek), deterministisk (fasta frön).
#

import math
import random

from learning.metrics import bootstrap_mean_ci

TRAIN_SHARE = 0.70


# ----------------------------------------------------------------
# Små hjälpare
# ----------------------------------------------------------------

def _solve(matrix, vector):
    #
    # Löser A·x = b med Gauss-elimination (partiell pivotering). Små
    # system (k <= ~15), därför ingen särskild bibliotekslösning.
    #
    n = len(vector)
    a = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ValueError("Singulär matris")
        a[col], a[pivot] = a[pivot], a[col]
        for row in range(col + 1, n):
            factor = a[row][col] / a[col][col]
            if factor:
                for c in range(col, n + 1):
                    a[row][c] -= factor * a[col][c]
    result = [0.0] * n
    for row in range(n - 1, -1, -1):
        total = a[row][n] - sum(a[row][c] * result[c] for c in range(row + 1, n))
        result[row] = total / a[row][row]
    return result


def _softmax(etas):
    top = max(etas)
    exps = [math.exp(e - top) for e in etas]
    total = sum(exps)
    return [e / total for e in exps]


def _race_nll(etas, winner):
    # -log P(vinnaren) = logsumexp(eta) - eta_vinnare
    top = max(etas)
    lse = top + math.log(sum(math.exp(e - top) for e in etas))
    return lse - etas[winner]


def sort_by_time(races):
    return sorted(races, key=lambda r: (r["date"] or "", str(r["key"])))


# ----------------------------------------------------------------
# Standardisering och anpassning
# ----------------------------------------------------------------

def standardization(races):
    #
    # Medel och standardavvikelse per signal över alla hästar i
    # träningsloppen. Konstant signal får sd = 1 (bidrar inget).
    #
    k = len(races[0]["x"][0])
    rows = [h for r in races for h in r["x"]]
    count = len(rows)
    means = [sum(h[j] for h in rows) / count for j in range(k)]
    sds = []
    for j in range(k):
        var = sum((h[j] - means[j]) ** 2 for h in rows) / count
        sds.append(math.sqrt(var) if var > 1e-12 else 1.0)
    return means, sds


def _standardize_races(races, means, sds):
    return [
        ([[(h[j] - means[j]) / sds[j] for j in range(len(means))] for h in r["x"]], r["winner"])
        for r in races
    ]


def _fit_z(zraces, k, ridge, start=None, max_iter=25):
    #
    # Newton-Raphson på standardiserade signaler. Returnerar γ.
    #
    gamma = list(start) if start else [0.0] * k

    def loglik(g):
        total = 0.0
        for z, winner in zraces:
            etas = [sum(g[j] * row[j] for j in range(k)) for row in z]
            total -= _race_nll(etas, winner)
        return total - 0.5 * ridge * sum(v * v for v in g)

    current = loglik(gamma)

    for _ in range(max_iter):
        grad = [-ridge * g for g in gamma]
        hess = [[0.0] * k for _ in range(k)]
        for z, winner in zraces:
            etas = [sum(gamma[j] * row[j] for j in range(k)) for row in z]
            probs = _softmax(etas)
            mean = [sum(p * row[j] for p, row in zip(probs, z)) for j in range(k)]
            for j in range(k):
                grad[j] += z[winner][j] - mean[j]
            for p, row in zip(probs, z):
                for a in range(k):
                    da = row[a] - mean[a]
                    if da == 0.0:
                        continue
                    pa = p * da
                    for b in range(a, k):
                        hess[a][b] += pa * (row[b] - mean[b])
        for a in range(k):
            for b in range(a):
                hess[a][b] = hess[b][a]
            hess[a][a] += ridge

        step = _solve(hess, grad)

        scale = 1.0
        improved = False
        for _ in range(12):
            candidate = [g + scale * s for g, s in zip(gamma, step)]
            value = loglik(candidate)
            if value >= current - 1e-12:
                improved = True
                break
            scale *= 0.5
        if not improved:
            break

        change = max(abs(c - g) for c, g in zip(candidate, gamma))
        gamma, current = candidate, value
        if change < 1e-6:
            break

    return gamma


def fit_conditional_logit(races, ridge=1.0, max_iter=25):
    #
    # Anpassar β på rådata-skala. Returnerar dict med β, medel, sd, γ.
    #
    means, sds = standardization(races)
    zraces = _standardize_races(races, means, sds)
    k = len(means)
    gamma = _fit_z(zraces, k, ridge, max_iter=max_iter)
    return {
        "beta": [g / s for g, s in zip(gamma, sds)],
        "gamma": gamma, "means": means, "sds": sds,
    }


def model_etas(model, race):
    # η = Σ γ_j · (x_j - medel_j)/sd_j  (konstant term faller bort i softmax)
    gamma, means, sds = model["gamma"], model["means"], model["sds"]
    return [
        sum(gamma[j] * (h[j] - means[j]) / sds[j] for j in range(len(gamma)))
        for h in race["x"]
    ]


# ----------------------------------------------------------------
# Nuvarande modell: temperatur på loggad Total Score
# ----------------------------------------------------------------

def fit_temperature(races, lo=0.0, hi=1.0, iterations=60):
    #
    # τ som minimerar log-loss för softmax(τ · poäng). Log-loss är
    # konvex i τ, så gyllene snittet räcker.
    #
    def total(tau):
        return sum(_race_nll([tau * s for s in r["scores"]], r["winner"]) for r in races)

    ratio = (math.sqrt(5) - 1) / 2
    a, b = lo, hi
    c = b - ratio * (b - a)
    d = a + ratio * (b - a)
    fc, fd = total(c), total(d)
    for _ in range(iterations):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - ratio * (b - a)
            fc = total(c)
        else:
            a, c, fc = c, d, fd
            d = a + ratio * (b - a)
            fd = total(d)
    return (a + b) / 2


def mean_log_loss(races, etas_fn):
    return sum(_race_nll(etas_fn(r), r["winner"]) for r in races) / len(races)


# ----------------------------------------------------------------
# Walk-forward: tränas på äldre lopp, prövas på nyare
# ----------------------------------------------------------------

def walk_forward(races, ridge=1.0, train_share=TRAIN_SHARE, seed=12345):
    ordered = sort_by_time(races)
    split = int(len(ordered) * train_share)
    train, test = ordered[:split], ordered[split:]

    tau = fit_temperature(train)
    model = fit_conditional_logit(train, ridge=ridge)

    current_losses = [_race_nll([tau * s for s in r["scores"]], r["winner"]) for r in test]
    fitted_losses = [_race_nll(model_etas(model, r), r["winner"]) for r in test]
    uniform = [math.log(len(r["scores"])) for r in test]
    deltas = [f - c for f, c in zip(fitted_losses, current_losses)]

    ci = bootstrap_mean_ci(deltas, seed=seed)
    delta = sum(deltas) / len(deltas)

    if ci is None:
        verdict = "för få testlopp"
    elif ci[1] < 0:
        verdict = "anpassade vikter bättre"
    elif ci[0] > 0:
        verdict = "nuvarande vikter bättre"
    else:
        verdict = "ingen påvisad skillnad"

    return {
        "n_train": len(train), "n_test": len(test),
        "train_from": train[0]["date"], "train_to": train[-1]["date"],
        "test_from": test[0]["date"], "test_to": test[-1]["date"],
        "tau": tau,
        "log_loss_current": sum(current_losses) / len(test),
        "log_loss_fitted": sum(fitted_losses) / len(test),
        "log_loss_uniform": sum(uniform) / len(test),
        "delta_mean": delta, "delta_ci": ci, "verdict": verdict,
    }


# ----------------------------------------------------------------
# Koefficienter med bootstrap över lopp
# ----------------------------------------------------------------

def coefficients(races, ridge=1.0, n_boot=60, seed=12345, level=0.95):
    full = fit_conditional_logit(races, ridge=ridge)
    means, sds = full["means"], full["sds"]
    k = len(means)
    zraces = _standardize_races(races, means, sds)

    rng = random.Random(seed)
    size = len(zraces)
    draws = [[] for _ in range(k)]
    for _ in range(n_boot):
        sample = [zraces[rng.randrange(size)] for _ in range(size)]
        try:
            gamma = _fit_z(sample, k, ridge, start=full["gamma"], max_iter=6)
        except ValueError:
            continue
        for j in range(k):
            draws[j].append(gamma[j] / sds[j])

    cis = []
    tail = (1 - level) / 2
    for j in range(k):
        values = sorted(draws[j])
        if len(values) < 10:
            cis.append(None)
            continue
        low = values[int(tail * len(values))]
        high = values[min(int((1 - tail) * len(values)), len(values) - 1)]
        cis.append((low, high))

    return {"beta": full["beta"], "ci": cis, "n_boot": n_boot, "tau": fit_temperature(races)}


# ----------------------------------------------------------------
# Mervärde för en kandidatsignal bortom nuvarande modell
# ----------------------------------------------------------------

def added_value(races, scale=10.0, ridge=0.01, n_boot=200, seed=12345, level=0.95):
    #
    # Modell: softmax(τ · poäng + γ · signal/scale). τ fast (anpassad på
    # samma lopp), γ fri. Returnerar γ per `scale` signalpoäng med
    # bootstrap-intervall och förbättringen i log-loss per lopp.
    #
    usable = [r for r in races if r.get("extra") is not None]
    if len(usable) < 2:
        return None

    tau = fit_temperature(usable)
    base = [[tau * s for s in r["scores"]] for r in usable]
    sig = [[e / scale for e in r["extra"]] for r in usable]
    winners = [r["winner"] for r in usable]

    def fit_gamma(indices, start=0.0, max_iter=25):
        gamma = start
        for _ in range(max_iter):
            grad = -ridge * gamma
            hess = ridge
            for i in indices:
                etas = [b + gamma * e for b, e in zip(base[i], sig[i])]
                probs = _softmax(etas)
                mean = sum(p * e for p, e in zip(probs, sig[i]))
                var = sum(p * (e - mean) ** 2 for p, e in zip(probs, sig[i]))
                grad += sig[i][winners[i]] - mean
                hess += var
            step = grad / hess
            gamma += step
            if abs(step) < 1e-8:
                break
        return gamma

    everything = list(range(len(usable)))
    gamma = fit_gamma(everything)

    gains = []
    for i in everything:
        before = _race_nll(base[i], winners[i])
        after = _race_nll([b + gamma * e for b, e in zip(base[i], sig[i])], winners[i])
        gains.append(before - after)
    gain_ci = bootstrap_mean_ci(gains, seed=seed)

    rng = random.Random(seed)
    draws = []
    for _ in range(n_boot):
        sample = [rng.randrange(len(usable)) for _ in usable]
        draws.append(fit_gamma(sample, start=gamma, max_iter=8))
    draws.sort()
    tail = (1 - level) / 2
    gamma_ci = (
        draws[int(tail * len(draws))],
        draws[min(int((1 - tail) * len(draws)), len(draws) - 1)],
    ) if len(draws) >= 10 else None

    #
    # Konservativt: "tillför information" kräver att BÅDE koefficientens
    # och förbättringens intervall ligger över 0. Bara det första är en
    # antydan, inte ett belägg.
    #
    gain_positive = gain_ci is not None and gain_ci[0] > 0
    if gamma_ci is None:
        verdict = "för få lopp"
    elif gamma_ci[0] > 0 and gain_positive:
        verdict = "tillför information"
    elif gamma_ci[0] > 0:
        verdict = "antydan, ej belagt"
    elif gamma_ci[1] < 0:
        verdict = "pekar åt fel håll"
    else:
        verdict = "ingen påvisad information"

    return {
        "n_races": len(usable), "scale": scale, "tau": tau,
        "gamma": gamma, "gamma_ci": gamma_ci,
        "gain_mean": sum(gains) / len(gains), "gain_ci": gain_ci,
        "verdict": verdict,
    }


# ----------------------------------------------------------------
# Helhet: allt rapporten behöver, i ett resultat
# ----------------------------------------------------------------

def run_weight_analysis(races, names, current_weights, propose, min_report,
                        min_tuning, ridge=1.0, n_boot=60):
    #
    # races           lopp i formen ovan
    # names           visningsnamn per signal (samma ordning som x)
    # current_weights nuvarande effektiv vikt per signal (samma ordning)
    # propose         funktion: lista β -> förslag (adapterns mappning) eller None
    # min_report      färre lopp än så -> bara antal redovisas
    # min_tuning      färre lopp än så -> resultatet märks preliminärt
    #
    result = {
        "n_races": len(races),
        "min_report": min_report, "min_tuning": min_tuning,
        "too_few": len(races) < min_report,
        "preliminary": len(races) < min_tuning,
        "walk_forward": None, "coefficients": None,
        "proposal": None, "expert": None,
    }
    if result["too_few"]:
        return result

    result["walk_forward"] = walk_forward(races, ridge=ridge)

    coef = coefficients(races, ridge=ridge, n_boot=n_boot)
    tau = coef["tau"]
    total_pos = sum(max(b, 0.0) for b in coef["beta"])
    total_now = sum(current_weights)
    rows = []
    for name, beta, ci, now in zip(names, coef["beta"], coef["ci"], current_weights):
        rows.append({
            "name": name,
            "current": tau * now,
            "beta": beta, "ci": ci,
            "share_current": now / total_now if total_now else None,
            "share_fitted": max(beta, 0.0) / total_pos if total_pos else None,
            "significant": ci is not None and (ci[0] > 0 or ci[1] < 0),
        })
    result["coefficients"] = {"rows": rows, "tau": tau, "n_boot": coef["n_boot"]}
    result["proposal"] = propose(coef["beta"])
    result["expert"] = added_value(races)
    return result
