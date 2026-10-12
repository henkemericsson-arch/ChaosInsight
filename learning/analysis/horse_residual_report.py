#
# Formaterar hästresidual-analysen till läsbar text. Ren formatering.
#


def _pct_ratio(value):
    return "    -" if value is None else f"{value:5.2f}"


def _variant_text(variant):
    decay = variant["decay"]
    history = ("hela historiken" if decay == 1.0
               else f"avtagande vikt {decay:g} per start")
    scope = ("historik per roll (favorit / tvåa-trea / övriga), används när rollen är densamma"
             if variant["scope"] == "role" else "all historik oavsett roll")
    return f"{history}; {scope}"


def format_horse_report(market, walk, title):
    lines = []
    out = lines.append

    out("=" * 72)
    out(f"HÄSTNIVÅ: UNDER-/ÖVERVÄRDERAS VISSA HÄSTAR? - {title}")
    out("=" * 72)
    out("Mäter om en hästs tidigare avvikelse mot marknaden förutsäger nästa start.")
    out("Strikt framåtriktat: historiken innehåller bara äldre lopp.")
    out("")

    out(f"Lopp i underlaget: {market['n_legs']} (dubbletter mellan spel borttagna)")
    out("")
    out("1. MARKNADENS EGEN SKEVHET (innan vi tittar på enskilda hästar)")
    out("-" * 72)
    out(f"Kalibreringsexponent k = {market['k']}  (k>1: långskott överskattas av odds)")
    out(f"  {'Oddsband':26}{'Starter':>10}{'Förväntat':>11}{'Faktiskt':>10}{'Kvot':>7}{'z':>7}")
    for b in market["bands"]:
        if b["n"] == 0 or "ratio" not in b:
            continue
        out(
            f"  {b['label']:26}{b['n']:>10}{b['expected']:>11.0f}{b['actual']:>10.0f}"
            f"{b['ratio']:>7.2f}{b['z']:>+7.1f}"
        )
    out("  Kvot = faktiska vinster / marknadens förväntan (1,00 = rätt prissatt).")
    out("  |z| över 2 = skillnaden är osannolik som ren slump.")

    out("")
    out(f"2. TEST: FÖRUTSÄGER HÄSTENS HISTORIK NÄSTA START? "
        f"({walk['n_legs']} lopp, kalibrerad marknad k={walk['k']})")
    out("-" * 72)
    out(f"Kvot per häst = (vinster + {walk['prior']:g}) / (förväntat + {walk['prior']:g}), "
        f"minst {walk['min_starts']} tidigare starter.")
    out("Marknadens sannolikhet justeras med kvot^beta. Delta log-loss mot ojusterad")
    out("marknad: negativt = hästens historik tillför information. * = säkerställt.")

    for variant in walk["variants"].values():
        out("")
        out(f"  Variant: {_variant_text(variant)}")
        for group_label, rows in variant["tilt"].items():
            if variant["scope"] == "role":
                out(f"  Roll: {group_label}")
            out(f"  {'beta':>6}{'Lopp':>9}{'Delta LL':>11}{'95% CI':>26}")
            for t in rows:
                if "mean_delta_log_loss" not in t:
                    continue
                low, high = t["ci95"]
                mark = "*" if (high < 0 or low > 0) else " "
                out(
                    f"  {t['beta']:>6.2f}{t['n_legs']:>9}{t['mean_delta_log_loss']:>+11.5f}"
                    f"{'(' + format(low, '+.5f') + ' .. ' + format(high, '+.5f') + ')':>26} {mark}"
                )

            better = [
                t for t in rows
                if "ci95" in t and t["ci95"][1] < 0
            ]
            if better:
                best = min(better, key=lambda t: t["mean_delta_log_loss"])
                out(f"  -> SIGNAL: historiken tillför information (bäst beta={best['beta']:g}, "
                    f"delta {best['mean_delta_log_loss']:+.5f}).")
            else:
                out("  -> Ingen säkerställd förbättring: historiken tillför inget utöver marknaden.")

    out("")
    out("3. NÄSTA START FÖR HÄSTAR MED OLIKA HISTORIK (oddsband eller roll, och hästens kvot)")
    out("-" * 72)
    out("Kvot = faktiska vinster / förväntade i NÄSTA start. Över 1 = underskattad.")
    for variant in walk["variants"].values():
        out("")
        out(f"  Variant: {_variant_text(variant)}")
        heading = "Roll / kvot före starten" if variant["scope"] == "role" else "Oddsband / kvot före starten"
        out(f"  {heading:44}{'Starter':>9}{'Kvot':>7}{'z':>7}")
        for b in variant["buckets"]:
            z = "" if b.get("z") is None else f"{b['z']:+.1f}"
            mark = "*" if b.get("z") is not None and abs(b["z"]) > 2 else " "
            out(f"  {b['label'][:43]:44}{b['n']:>9}{_pct_ratio(b.get('ratio')):>7}{z:>7} {mark}")

    out("")
    out("Roll = hästens rang i marknaden i just det loppet. 'Favoriten som brukar missa'")
    out("syns som kvot under 1 i raden 'favorit' efter låg kvot före; 'trean som brukar vinna'")
    out("som kvot över 1 i raden 'tvåa/trea'.")
    out("")
    out("Så läser du den: finns en riktig, varaktig under-/övervärdering ska hästar med")
    out("hög kvot före starten ha kvot över 1 i NÄSTA start, och beta ska ge negativt delta")
    out("med säkerställt konfidensintervall. Annars är mönstren i efterhand slump eller")
    out("marknadens allmänna skevhet (avsnitt 1), inte något hästen 'brukar'.")
    return "\n".join(lines)
