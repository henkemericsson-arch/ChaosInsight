#
# Tips -> expert_index per hast (0-100). Ren funktion utan I/O.
# Samma modell oavsett domän - bara ordlistans vikter (lexicon) och
# kallvikterna (config) ar domanspecifika data.
#
# Per kalla och hast: stod = starkaste signalen + en fjardedel av ovriga
# (rangordning ger 0..vikt efter placering), tak SUPPORT_CAP, negativt blir 0.
# Index = viktat medel over de kallor som alls haft tips i loppet
# (en kalla utan tips for loppet raknas inte - saknad ar inte "nej").
#


def _signal_support(tip, weights):
    if tip.signal == "rank":
        if not tip.rank or not tip.rank_of:
            return 0.0
        share = 1.0 - (tip.rank - 1) / max(tip.rank_of, 1)
        return weights.get("rank_top", 0.0) * share * tip.confidence
    return weights.get(tip.signal, 0.0) * tip.confidence


OVERLAP_SHARE = 0.25


def _combine(parts, cap):
    # Signaler fran samma kalla om samma hast overlappar ofta (rank + system
    # + prosa sager samma sak), sa starkaste signalen raknas fullt och
    # ovriga med OVERLAP_SHARE. Avrad (negativt) drar ner direkt.
    positives = [p for p in parts if p > 0]
    negatives = sum(p for p in parts if p < 0)
    if positives:
        top = max(positives)
        support = top + OVERLAP_SHARE * (sum(positives) - top) + negatives
    else:
        support = negatives
    return max(0.0, min(cap, support))


def leg_index(tips_for_leg, roster_numbers, weights, cap, source_weights=None):
    # tips_for_leg: lista ExpertTip (ett lopp). Returnerar {hast: index} eller {}.
    source_weights = source_weights or {}
    by_source = {}
    for tip in tips_for_leg:
        by_source.setdefault(tip.source, []).append(tip)
    if not by_source:
        return {}

    total_weight = sum(source_weights.get(s, 1.0) for s in by_source)
    result = {}
    for number in roster_numbers:
        weighted = 0.0
        for source, source_tips in by_source.items():
            parts = [
                _signal_support(t, weights) for t in source_tips if t.horse_number == number
            ]
            support = _combine(parts, cap)
            weighted += source_weights.get(source, 1.0) * (support / cap)
        result[number] = round(100.0 * weighted / total_weight, 1)
    return result
