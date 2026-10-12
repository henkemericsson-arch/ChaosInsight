#
# Textrapport för viktanalysen (005 avsnitt 17). Presentation av färdiga
# resultat - ingen beräkning här.
#


def _ci(ci, digits=3):
    if ci is None:
        return "   –"
    return f"[{ci[0]:+.{digits}f}, {ci[1]:+.{digits}f}]"


def format_weight_report(result, meta=None):
    meta = meta or {}
    lines = []
    add = lines.append

    add("=" * 62)
    add("VIKTANALYS (etapp 2a)")
    add("=" * 62)
    add(f"Lopp med alla delpoäng: {result['n_races']}")
    for label, count in (meta.get("dropped") or {}).items():
        if count:
            add(f"  bortfall – {label}: {count}")
    info = meta.get("info") or {}
    if info.get("trend_imputed_races"):
        add(f"  lopp där trend saknades (neutralt 50 användes): {info['trend_imputed_races']}")
    versions = info.get("versions") or {}
    if len(versions) > 1:
        add("  OBS: flera parameter-/kodversioner blandas:")
        for (pv, cv), n in sorted(versions.items(), key=lambda kv: str(kv[0])):
            add(f"    parameter_version {pv}, code_version {cv}: {n} lopp")

    if result["too_few"]:
        add("")
        add(f"För lite data: kräver minst {result['min_report']} lopp för att anpassa något.")
        add("Delpoängen loggas först från och med parameterlagret (005 avsnitt 16);")
        add("äldre lopp saknar dem och kan inte räknas om. Kör igen när fler spel utvärderats.")
        return "\n".join(lines)

    if result["preliminary"]:
        add("")
        add(f"PRELIMINÄRT: {result['n_races']} lopp av de {result['min_tuning']} som krävs för justering.")
        add("Läs resultatet som en riktning, inte som underlag för ändring.")

    wf = result["walk_forward"]
    add("")
    add("-" * 62)
    add("1. Slår anpassade vikter nuvarande Total Score? (walk-forward)")
    add("-" * 62)
    add(f"Träning: {wf['n_train']} lopp ({wf['train_from']} – {wf['train_to']})")
    add(f"Test:    {wf['n_test']} lopp ({wf['test_from']} – {wf['test_to']}) – ej sedda vid anpassning")
    add(f"Log-loss per lopp på testdelen (lägre = bättre):")
    add(f"  nuvarande Total Score : {wf['log_loss_current']:.4f}")
    add(f"  anpassade vikter      : {wf['log_loss_fitted']:.4f}")
    add(f"  slumpen (lika chans)  : {wf['log_loss_uniform']:.4f}")
    add(f"Skillnad (anpassad − nuvarande): {wf['delta_mean']:+.4f}  95 % KI {_ci(wf['delta_ci'], 4)}")
    add(f"Slutsats: {wf['verdict']}")

    coef = result["coefficients"]
    add("")
    add("-" * 62)
    add("2. Vilka signaler förklarar vinnare? (alla lopp)")
    add("-" * 62)
    add(f"Koefficient per poäng (jämförbar med nuvarande = τ·vikt, τ={coef['tau']:.4f}).")
    add(f"KI = bootstrap över lopp ({coef['n_boot']} omtagningar). * = skiljer sig från 0.")
    add(f"{'Signal':<11}{'nuv.':>8}{'anpassad':>10}  {'95 % KI':<20}{'andel nu':>9}{'andel ny':>9}")
    for row in coef["rows"]:
        star = "*" if row["significant"] else " "
        now_share = "–" if row["share_current"] is None else f"{100 * row['share_current']:.0f}%"
        new_share = "–" if row["share_fitted"] is None else f"{100 * row['share_fitted']:.0f}%"
        add(
            f"{row['name']:<11}{row['current']:>8.4f}{row['beta']:>10.4f}{star} "
            f"{_ci(row['ci'], 4):<20}{now_share:>8}{new_share:>9}"
        )

    add("")
    add("-" * 62)
    add("3. Förslag i parametrarnas termer (information – inget ändras)")
    add("-" * 62)
    proposal = result["proposal"]
    if proposal is None:
        add("Inget förslag: alla koefficienter är <= 0.")
    else:
        add(f"{'Parameter':<24}{'nu':>9}{'förslag':>10}")
        current = meta.get("current_params") or {}
        for name in sorted(proposal):
            now = current.get(name)
            if now is None:
                continue
            if abs(proposal[name] - now) < 1e-9:
                continue
            add(f"{name:<24}{now:>9.3f}{proposal[name]:>10.3f}")
        if wf["verdict"] != "anpassade vikter bättre":
            add("")
            add("Förslaget är INTE belagt: anpassade vikter har inte slagit nuvarande")
            add("på osedda lopp (punkt 1). Etapp 4 skulle avvisa det.")

    add("")
    add("-" * 62)
    add("4. Tillför expertindexet något utöver Total Score?")
    add("-" * 62)
    expert = result["expert"]
    if expert is None:
        add("Inga lopp med expertindex för alla hästar ännu.")
    else:
        add(f"Lopp med expertindex: {expert['n_races']}")
        add(f"γ per {expert['scale']:.0f} indexpoäng: {expert['gamma']:+.4f}  95 % KI {_ci(expert['gamma_ci'], 4)}")
        add(f"Förbättring i log-loss per lopp: {expert['gain_mean']:+.4f}  95 % KI {_ci(expert['gain_ci'], 4)}")
        add(f"Slutsats: {expert['verdict']}")
        if expert["n_races"] < result["min_tuning"]:
            add(f"(Få lopp – {expert['n_races']} av {result['min_tuning']} – tolka försiktigt.)")

    return "\n".join(lines)
