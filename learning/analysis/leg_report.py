from learning.analysis.calibration_report import LABELS, _pct

#
# Formaterar leg_analysis-resultat till läsbar text. Ren formatering.
#

STRATEGY_LABELS = {
    "continuous": "KAMT v1 (continuous)",
    "legacy": "KAMT v1 (legacy)",
    "kamt_v2": "KAMT v2",
}


def _ci(value, ci):
    if value is None:
        return "-"
    if not ci:
        return f"{value * 100:+.1f} pe"
    return f"{value * 100:+.1f} pe (95% CI {ci[0] * 100:+.1f} .. {ci[1] * 100:+.1f})"


def _selection_block(out, title, analysis, what):
    out(title)
    out("-" * 72)

    if not analysis["n_games"]:
        out("  För få spel med fullständiga lopp för att räkna.")
        out("")
        return

    out(
        f"{analysis['n_games']} spel, {analysis['n_legs']} lopp. "
        f"Slumpvald {what}: {_pct(analysis['baseline']).strip()}"
    )
    if analysis["n_games"] < 30:
        out("OBS: under 30 spel - resultaten är mycket osäkra.")
    out("")
    out(f"  {'Kriterium':46}{'@1':>7}{'@2':>7}{'@3':>7}{'AUC':>7}")
    for name, c in analysis["criteria"].items():
        auc = "  -  " if c["auc"] is None else f"{c['auc']:.2f}"
        out(
            f"  {c['label'][:45]:46}{_pct(c['hit1']):>7}{_pct(c['hit2']):>7}"
            f"{_pct(c['hit3']):>7}{auc:>7}"
        )
    out("")
    out(f"  @s = {what} i de s lopp per spel som kriteriet rankar högst.")
    out("  AUC = sannolikhet att ett lopp där det gick bra rankas över ett där det")
    out("  inte gick bra, inom samma spel (0,50 = slump, 1,00 = perfekt).")
    out("  Skillnad mot marknadens odds på @1 (procentenheter, bootstrap över spel):")
    for name, c in analysis["criteria"].items():
        if "delta1_vs_market" not in c:
            continue
        out(f"    {c['label'][:45]:46}{_ci(c['delta1_vs_market'], c['delta1_ci95'])}")
    out("")


def format_leg_report(selection, kaos, coverage, title, skipped=None):
    lines = []
    out = lines.append

    out("=" * 72)
    out(f"SPIK/LÅS-, KAOS- OCH TÄCKNINGSRAPPORT - {title}")
    out("=" * 72)
    if skipped:
        parts = [f"{k}: {v}" for k, v in skipped.items() if v]
        if parts:
            out("Bortsorterat: " + "; ".join(parts))
    out("")

    n = 1
    for model, blocks in selection.items():
        label = LABELS.get(model, model)
        _selection_block(
            out,
            f"{n}. SPIKURVAL - {label}: vilken favorits lopp är säkrast att spika?",
            blocks["spike"], "favoritträff",
        )
        n += 1
        _selection_block(
            out,
            f"{n}. LÅSURVAL - {label}: vilka lopp är säkrast att låsa "
            f"(två främsta favoriterna)?",
            blocks["lock"], "låsträff",
        )
        n += 1

    out(f"{n}. KAOSVÄRDE: är höga kaosvärden svårare lopp? (grupper efter kaosvärde)")
    out("-" * 72)
    for model, rows in kaos.items():
        out(LABELS.get(model, model))
        if not rows:
            out("  För få lopp.")
            continue
        out(f"  {'Kaosvärde':>14}{'Lopp':>6}{'Favorit':>9}{'Mark top2':>11}"
            f"{'Mark top3':>11}{'Mod top3':>10}")
        for r in rows:
            span = f"{r['kaos_min']:.0f}-{r['kaos_max']:.0f}"
            out(
                f"  {span:>14}{r['n_legs']:>6}{_pct(r['fav_win']):>9}"
                f"{_pct(r['mkt_top2']):>11}{_pct(r['mkt_top3']):>11}"
                f"{_pct(r['mod_top3']):>10}"
            )
    out("  Om kaosvärdet fungerar: träffprocenten faller från första till sista raden.")
    out("")
    n += 1

    out(f"{n}. TÄCKNING: fanns vinnaren bland de valda hästarna?")
    out("-" * 72)
    out("Jämfört med marknadens topp-N (odds) med exakt lika många hästar i loppet.")
    for strategy, c in coverage.items():
        out("")
        out(STRATEGY_LABELS.get(strategy, strategy))
        if not c.get("n_legs"):
            out("  Inga lopp med sparade val.")
            continue
        out(
            f"  {c['n_legs']} lopp, snittbredd {c['mean_width']:.2f} hästar. "
            f"Täckning: system {_pct(c['ours']).strip()}, "
            f"marknad {_pct(c['market']).strip()}"
        )
        out(f"  Skillnad: {_ci(c['delta'], c['delta_ci95'])}")
        out(f"  {'Bredd':>8}{'Lopp':>6}{'System':>9}{'Marknad':>9}")
        for r in c["by_width"]:
            out(
                f"  {r['width']:>8}{r['n_legs']:>6}{_pct(r['ours']):>9}"
                f"{_pct(r['market']):>9}"
            )
        if c["n_differing"]:
            out(
                f"  Lopp där systemet valde annorlunda än marknaden: "
                f"{c['n_differing']} st. Där hade systemet vinnaren i "
                f"{_pct(c['differing_ours']).strip()}, marknadens val i "
                f"{_pct(c['differing_market']).strip()}."
            )
        if c["skipped_no_choice"]:
            out(f"  ({c['skipped_no_choice']} lopp saknade sparade val och räknades inte.)")

    out("")
    out("pe = procentenheter. Med få spel/lopp är allt osäkert - läs konfidensintervallen.")
    return "\n".join(lines)
