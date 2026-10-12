from learning.analysis.calibration_report import _pct
from learning.analysis.leg_report import STRATEGY_LABELS

#
# Formaterar miss_analysis-resultat till läsbar text. Ren formatering.
#


def _delta(value, ci):
    if value is None:
        return "      -"
    mark = " "
    if ci and (ci[0] > 0 or ci[1] < 0):
        mark = "*"
    return f"{value:+7.2f}{mark}"


def format_miss_report(analyses, title, skipped=None):
    lines = []
    out = lines.append

    out("=" * 72)
    out(f"MISSANALYS - {title}")
    out("=" * 72)
    out("Lär av de egna prediktionerna: vad gick rätt, vad gick fel och varför.")
    if skipped:
        parts = [f"{k}: {v}" for k, v in skipped.items() if v]
        if parts:
            out("Bortsorterat: " + "; ".join(parts))

    for strategy, a in analyses.items():
        out("")
        out("#" * 72)
        out(STRATEGY_LABELS.get(strategy, strategy))
        out("#" * 72)

        if not a.get("n_legs"):
            out("Inga lopp med sparade val.")
            continue

        out(
            f"{a['n_legs']} lopp: {a['n_hit']} träffar "
            f"({_pct(a['hit_rate']).strip()}), {a['n_miss']} missar."
        )
        kinds = a["hit_kinds"]
        out(
            f"Träffar fördelade på: spik {kinds['spik']}, lås {kinds['lås']}, "
            f"gardering {kinds['gardering']}."
        )

        out("")
        out("1. VARFÖR MISSADE VI? (orsaksklass, första träffande regel)")
        out("-" * 72)
        for c in a["miss_classes"]:
            if not c["n"]:
                continue
            share = c["n"] / a["n_miss"] if a["n_miss"] else 0
            out(f"  {c['label'][:56]:57}{c['n']:>4}  {_pct(share)}")
        out("  Skräll = vinnaren hade marknadsodds på 10 eller mer.")

        out("")
        out("2. TRÄFF PER VINNARENS ODDS (hur täcker vi skrällar?)")
        out("-" * 72)
        out(f"  {'Vinnarens odds':16}{'Lopp':>6}{'Träff':>9}")
        for r in a["by_winner_odds"]:
            out(f"  {r['band']:16}{r['n_legs']:>6}{_pct(r['hit_rate']):>9}")

        out("")
        out("3. TRÄFF PER KAOSVÄRDE (gardera vi bredare när det är svårt?)")
        out("-" * 72)
        if a["by_kaos"]:
            out(f"  {'Kaosvärde':14}{'Lopp':>6}{'Träff':>9}{'Snittbredd':>12}")
            for r in a["by_kaos"]:
                span = f"{r['kaos_min']:.0f}-{r['kaos_max']:.0f}"
                out(
                    f"  {span:14}{r['n_legs']:>6}{_pct(r['hit_rate']):>9}"
                    f"{r['mean_width']:>12.2f}"
                )
        else:
            out("  För få lopp med kaosvärde.")

        out("")
        out("4. GALOPP/DISKNING (otur snarare än modellfel)")
        out("-" * 72)
        out(
            f"  Missade lopp där minst en vald häst galopperade/diskades: "
            f"{_pct(a['misses_with_chosen_galloping']).strip()}"
        )
        out(
            f"  Träffade lopp där det hände: "
            f"{_pct(a['hits_with_chosen_galloping']).strip()}"
        )

        out("")
        out("5. VAD SKILJER DEN VINNANDE HÄSTEN FRÅN DE VALDA? (vinnare minus valda)")
        out("-" * 72)
        out("  Positivt = vinnaren hade högre värde än de valda hästarna i loppet.")
        out("  * = konfidensintervallet (95 %) utesluter 0.")
        out(f"  {'Egenskap':22}{'Missar':>8}{'Lopp':>6}{'Träffar':>10}{'Lopp':>6}")
        for f in a["features"]:
            out(
                f"  {f['label']:22}{_delta(f['delta_miss'], f['ci_miss']):>8}"
                f"{f['n_miss']:>6}{_delta(f['delta_hit'], f['ci_hit']):>10}"
                f"{f['n_hit']:>6}"
            )
        out("  'Missar' visar vad de missade vinnarna hade som vi underskattade.")
        out("  'Träffar' är jämförelsen när vi hade vinnaren (normalbilden).")
        out("  Med nio egenskaper kan en stjärna uppstå av en slump; se det som hypoteser.")

    out("")
    out("Allt är hypoteser tills fler lopp finns. Rapporten ändrar inget i systemet.")
    return "\n".join(lines)
