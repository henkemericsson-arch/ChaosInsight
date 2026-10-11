#
# Gör en kalibreringsrapport (dict från compute_calibration) till
# läsbar text. Ren formatering - inga beräkningar här.
#

LABELS = {
    "kamt_v1": "KAMT v1",
    "kamt_v2": "KAMT v2",
    "market_odds": "Marknad (odds)",
    "market_streck": "Marknad (streck)",
}


DIMENSIONS = {
    "track": "bana",
    "distance_class": "distans",
    "start_method": "start",
}


def _label_text(text):
    for key, label in LABELS.items():
        text = text.replace(key, label)
    return text


def _summary_table(out, summary, heading):
    out(heading)
    out(f"{'':18}{'Lopp':>6}{'Brier':>9}{'LogLoss':>9}{'Top1':>8}{'Top2':>8}{'Top3':>8}")
    for predictor, s_ in summary.items():
        if not s_["n_races"]:
            continue
        out(
            f"{LABELS.get(predictor, predictor):18}{s_['n_races']:>6}"
            f"{_num(s_['brier']):>9}{_num(s_['log_loss']):>9}"
            f"{_pct(s_['top1']):>8}{_pct(s_['top2']):>8}{_pct(s_['top3']):>8}"
        )


def _pct(value):
    return "  -  " if value is None else f"{value * 100:5.1f}%"


def _num(value, decimals=4):
    return "   -   " if value is None else f"{value:.{decimals}f}"


def format_report(report, title, min_races_for_tuning, skipped=None):
    lines = []
    out = lines.append

    out("=" * 72)
    out(f"KALIBRERINGSRAPPORT - {title}")
    out("=" * 72)
    out(f"Avgjorda lopp i underlaget: {report['n_races_total']}")

    for model in report["models"]:
        n = report["summary"][model]["n_races"]
        out(
            f"  {LABELS.get(model, model)}: {n} lopp "
            f"({n / min_races_for_tuning * 100:.0f}% av de "
            f"{min_races_for_tuning} som automatisk justering kräver)"
        )

    if report["field_conflicts"]:
        out(
            f"  OBS: {report['field_conflicts']} modell-lopp hade avvikande "
            f"startfält och uteslöts ur jämförelsen."
        )

    if skipped:
        parts = [f"{k}: {v}" for k, v in skipped.items() if v]
        if parts:
            out("  Bortsorterat: " + "; ".join(parts))

    out("")
    out("1. SAMMANFATTNING (lägre Brier/Log-loss = bättre)")
    out("-" * 72)
    out("Rå = poängen omräknade till andelar rakt av. Skärpejusterad = efter att")
    out("en enda exponent k anpassats så att sannolikheterna blir kalibrerade.")
    out("Skärpejusterad är den rättvisa jämförelsen av hur bra rangordningen är.")
    out("")
    _summary_table(out, report["summary"], "RÅ")
    out("")
    _summary_table(out, report["summary_calibrated"], "SKÄRPEJUSTERAD")
    sharp = report.get("sharpness", {})
    parts = [
        f"{LABELS.get(p, p)} k={k}" for p, k in sharp.items() if k is not None
    ]
    if parts:
        out("Anpassad skärpa: " + ", ".join(parts)
            + "  (k>1 = poängen var för platta, k<1 = för spetsiga, k=1 = redan rätt)")
    out("Top1/2/3 = hur ofta vinnaren fanns bland modellens 1/2/3 högst rankade.")
    out("OBS: raderna har olika antal lopp. Rättvis jämförelse: se avsnitt 2.")

    out("")
    out("2. JÄMFÖRELSE PÅ EXAKT SAMMA LOPP (delta log-loss, negativt = första bättre)")
    out("-" * 72)
    for title_, comps in (
        ("Rå", report["comparisons"]),
        ("Skärpejusterad", report["comparisons_calibrated"]),
    ):
        out(title_ + ":")
        for c in comps:
            a_ = LABELS.get(c["a"], c["a"])
            b_ = LABELS.get(c["b"], c["b"])
            if "mean_delta_log_loss" not in c:
                out(f"  {a_} mot {b_}: {c['n_races']} lopp - {_label_text(c['verdict'])}")
                continue
            low, high = c["ci95"]
            out(
                f"  {a_} mot {b_}: {c['n_races']} lopp, delta "
                f"{c['mean_delta_log_loss']:+.4f} (95% CI {low:+.4f} .. {high:+.4f})"
                f" -> {_label_text(c['verdict'])}"
            )
            out(
                f"      Top1 på dessa lopp: {a_} {_pct(c['top1_a']).strip()}, "
                f"{b_} {_pct(c['top1_b']).strip()}"
            )

    out("")
    out("3. KALIBRERING (säger modellen 20% - vinner hästarna ca 20%?)")
    out("-" * 72)
    tables = []
    for predictor in report["models"]:
        tables.append((LABELS.get(predictor, predictor) + " (rå)",
                       report["reliability"][predictor]))
        tables.append((LABELS.get(predictor, predictor) + " (skärpejusterad)",
                       report["reliability_calibrated"][predictor]))
    tables.append((LABELS["market_odds"], report["reliability"]["market_odds"]))
    for label, table in tables:
        out(label)
        out(f"  {'Intervall':>12}{'Hästar':>8}{'Prognos':>10}{'Faktiskt':>10}")
        for r in table:
            if not r["n"]:
                continue
            interval = f"{r['low'] * 100:.0f}-{r['high'] * 100:.0f}%"
            out(
                f"  {interval:>12}{r['n']:>8}"
                f"{_pct(r['mean_predicted']):>10}{_pct(r['actual_rate']):>10}"
            )

    out("")
    out("4. VINNARENS PLACERING I MODELLENS RANGORDNING")
    out("-" * 72)
    for predictor in report["models"]:
        dist = report["summary"][predictor].get("winner_rank_distribution", {})
        labels = ["1", "2", "3", "4", "5", "6+"]
        text = "  ".join(f"{k}:{dist.get(k, 0)}" for k in labels)
        out(f"{LABELS.get(predictor, predictor):10} {text}")

    out("")
    out("5. PER BANA / DISTANS / STARTMETOD (modell mot marknadsodds)")
    out("-" * 72)
    for model in report["models"]:
        rows = report["segments"].get(model, [])
        out(LABELS.get(model, model))
        if not rows:
            out("  (inga segment med tillräckligt många lopp)")
            continue
        out(f"  {'Segment':32}{'Lopp':>5}{'Top1 mod':>10}{'Top1 mark':>10}{'LL mod':>8}{'LL mark':>8}")
        for r in rows:
            name = f"{DIMENSIONS.get(r['dimension'], r['dimension'])}: {r['value']}"[:31]
            out(
                f"  {name:32}{r['n_races']:>5}{_pct(r['top1_model']):>10}"
                f"{_pct(r['top1_market']):>10}{_num(r['log_loss_model'], 3):>8}"
                f"{_num(r['log_loss_market'], 3):>8}"
            )

    out("")
    out("6. UTVECKLING PER VECKA (skärpejusterad, mot marknadsodds på samma lopp)")
    out("-" * 72)
    for model in report["models"]:
        rows = report["periods"].get(model, [])
        out(LABELS.get(model, model))
        if not rows:
            out("  (för få lopp per vecka)")
            continue
        out(f"  {'Vecka':10}{'Lopp':>5}{'Top1 mod':>10}{'Top1 mark':>10}{'Delta LL':>10}")
        for r in rows:
            out(
                f"  {r['period']:10}{r['n_races']:>5}{_pct(r['top1_model']):>10}"
                f"{_pct(r['top1_market']):>10}{r['delta_log_loss']:>+10.3f}"
            )
    out("Delta LL: negativt = modellen bättre än marknaden den veckan.")

    out("")
    out("Läs rapporten försiktigt: med få lopp är allt brus. Delta-raden (2) med")
    out("konfidensintervall säger om en skillnad är säkerställd; 'ingen säker")
    out("skillnad' betyder att datat ännu inte räcker för en slutsats.")

    return "\n".join(lines)
