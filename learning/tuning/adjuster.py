#
# Adjuster - bygger en kandidat-uppsättning ur ett förslag (005 avsnitt 18.2).
# Ren beräkning utan I/O. Guard verifierar resultatet oberoende.
#
# Steg per parameter:
#   1. dämpning     ny = gammal + η · (föreslagen − gammal)
#   2. stegtak      högst ±step_cap relativt gällande värde
#   3. totalt tak   högst ±total_cap relativt baseline
# Grupper som måste ha konstant summa (t.ex. score.crowd + score.chaos)
# behandlas som en fri parameter där den andra följer.
#


def allowed_interval(old, base, step_cap, total_cap):
    low = max(old * (1 - step_cap), base * (1 - total_cap))
    high = min(old * (1 + step_cap), base * (1 + total_cap))
    if low > high:
        # Gällande värde ligger redan utanför det totala taket: närmast tillåtna.
        nearest = min(max(old, base * (1 - total_cap)), base * (1 + total_cap))
        return nearest, nearest
    return low, high


def _clamp(value, low, high):
    return min(max(value, low), high)


def build_candidate(current, proposal, baseline, damping, step_cap, total_cap,
                    adjustable, sum_groups=()):
    candidate = dict(current)

    for name in adjustable:
        old = current[name]
        damped = old + damping * (proposal[name] - old)
        low, high = allowed_interval(old, baseline[name], step_cap, total_cap)
        candidate[name] = _clamp(damped, low, high)

    for first, second in sum_groups:
        total = current[first] + current[second]
        old = current[first]
        damped = old + damping * (proposal[first] - old)

        low_a, high_a = allowed_interval(old, baseline[first], step_cap, total_cap)
        low_b, high_b = allowed_interval(
            current[second], baseline[second], step_cap, total_cap
        )
        low = max(low_a, total - high_b)
        high = min(high_a, total - low_b)
        if low > high:
            candidate[first], candidate[second] = current[first], current[second]
            continue

        candidate[first] = _clamp(damped, low, high)
        candidate[second] = total - candidate[first]

    return candidate
