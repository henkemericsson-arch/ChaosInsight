"""
Engangsskript som uppgraderar KAMT v2:s skugglage i /resultat -
fran att bara visa en favorit per lopp till att generera ett
FULLSTANDIGT skuggsystem (spikar, las, gardering per lopp), genom
att atervanda den befintliga SystemGenerator.

Ersatter det block som script/patch_kamt_v2_shadow.py satte in
tidigare (kravs att den korts forst). Hittar block-granserna via
unik textinnehall, inte exakt whitespace.

Kor fran projektroten:
    python script/patch_kamt_v2_full_system.py
"""

import sys

APP_PATH = "web_app/app.py"


def find_line_index(lines, needle, label):
    matches = [i for i, line in enumerate(lines) if needle in line]
    if len(matches) != 1:
        print(f"AVBRUTET: hittade '{needle}' pa {len(matches)} rader for '{label}' (forvantade exakt 1).")
        print("Ingenting har andrats. Granska filen manuellt.")
        sys.exit(1)
    return matches[0]


def leading_whitespace(line):
    return line[:len(line) - len(line.lstrip())]


def main():
    with open(APP_PATH, encoding="utf-8") as f:
        lines = f.readlines()

    #
    # Patch 1: ersatt hela det tidigare inklistrade Python-blocket
    # (fran "kamt_v2_shadow = []" till och med felutskriften i
    # except-satsen) med den nya, fullstandiga
    # systemgenereringslogiken.
    #
    start_idx = find_line_index(
        lines, "och loggas for framtida utvardering, men paverkar ALDRIG",
        "borjan av forra kamt_v2-blocket (unik kommentarrad)",
    )
    #
    # Den hittade raden ar mitt i den gamla kommentaren - backa
    # upp genom HELA kommentarblocket (alla rader som borjar med
    # "#", inte bara tomma "#"-rader) tills vi nar kommentarens
    # egen borjan.
    #
    while start_idx > 0 and lines[start_idx - 1].strip().startswith("#"):
        start_idx -= 1
    end_idx = find_line_index(
        lines, "[KAMT v2 skugglage] Fel", "slutet av forra kamt_v2-blocket (felutskriften)"
    )

    if end_idx < start_idx:
        print("AVBRUTET: slutraden hittades fore startraden - nagot ovantat i filens struktur.")
        sys.exit(1)

    indent = leading_whitespace(lines[start_idx])

    new_block = (
        f'{indent}#\n'
        f'{indent}# KAMT v2 (skuggat/parallellt lage, experimentellt) -\n'
        f'{indent}# genererar ett FULLSTANDIGT skuggsystem via samma\n'
        f'{indent}# SystemGenerator som anvands for det riktiga systemet\n'
        f'{indent}# ovan, bara med KAMT v2:s Monte Carlo-sannolikheter som\n'
        f'{indent}# indata istallet for KAMT v1:s Total Score. Paverkar\n'
        f'{indent}# ALDRIG vilka hastar som faktiskt valjs i systemet ovan.\n'
        f'{indent}# Om nagot gar fel har ska det aldrig stoppa den riktiga\n'
        f'{indent}# systemgenereringen.\n'
        f'{indent}#\n'
        f'{indent}kamt_v2_shadow_legs = []\n'
        f'{indent}kamt_v2_shadow_cost = 0\n'
        f'{indent}try:\n'
        f'{indent}    from kamt_v2_forecast_logger import KamtV2ForecastLogger\n'
        f'{indent}    from kamt_v2_system_generator import generate_shadow_system\n'
        f'\n'
        f'{indent}    kamt_v2_logger = KamtV2ForecastLogger()\n'
        f'{indent}    kamt_v2_predictions = kamt_v2_logger.log_game(\n'
        f'{indent}        analysis_data.races, game_id=analysis_data.game.id,\n'
        f'{indent}        weather=analysis_data.weather,\n'
        f'{indent}    )\n'
        f'\n'
        f'{indent}    kamt_v2_leg_selections, kamt_v2_shadow_cost = generate_shadow_system(\n'
        f'{indent}        analysis_data.races, kamt_v2_predictions,\n'
        f'{indent}        max_cost=max_cost, risk=risk, spikes=spikes, locks=locks,\n'
        f'{indent}        game_type=analysis_data.game.name,\n'
        f'{indent}    )\n'
        f'\n'
        f'{indent}    kamt_v2_shadow_legs = sorted(\n'
        f'{indent}        kamt_v2_leg_selections, key=lambda leg: leg["race"].race_number\n'
        f'{indent}    )\n'
        f'{indent}except Exception as exc:\n'
        f'{indent}    print(f"[KAMT v2 skugglage] Fel (paverkar inte riktiga systemet): {{exc}}")\n'
    )

    lines[start_idx:end_idx + 1] = [new_block]

    #
    # Patch 2: ersatt det tidigare mallblocket (som bara visade en
    # rad per lopp) med ett som visar hela skuggsystemet - samma
    # kortlayout som det riktiga systemet ovan, plus total kostnad.
    #
    old_template_start = find_line_index(
        lines, "{% if kamt_v2_shadow %}", "gamla mallblockets start"
    )
    old_template_end = find_line_index(
        lines, "{{ pick.probability }}", "gamla mallblockets kärna (probability-raden)"
    )
    #
    # Mallblocket avslutas tva rader efter probability-raden
    # ({% endfor %} och {% endif %}) - hitta ratt slutindex genom
    # att leta efter naromraket "{% endif %}" efter old_template_end.
    #
    template_end_idx = None
    for i in range(old_template_end, min(old_template_end + 6, len(lines))):
        if "{% endif %}" in lines[i]:
            template_end_idx = i
            break

    if template_end_idx is None:
        print("AVBRUTET: hittade inte slutet pa det gamla mallblocket.")
        sys.exit(1)

    indent2 = leading_whitespace(lines[old_template_start])

    new_template = (
        f'{indent2}{{% if kamt_v2_shadow_legs %}}\n'
        f'{indent2}<h2>KAMT v2 (experimentell, skuggad)</h2>\n'
        f'{indent2}<p style="color:#8b949e; font-size:0.85rem;">\n'
        f'{indent2}    Kor parallellt for utvardering - paverkar inte systemet ovan.\n'
        f'{indent2}</p>\n'
        f'{indent2}<p>Total kostnad: <b>{{{{ kamt_v2_shadow_cost }}}} kr</b></p>\n'
        f'{indent2}{{% for leg in kamt_v2_shadow_legs %}}\n'
        f'{indent2}<div class="card leg">\n'
        f'{indent2}    <b>{{{{ leg.race }}}}</b>\n'
        f'{indent2}    <div class="kaos">Kaosvärde: {{{{ "%.1f"|format(leg.race.kaosvarde or 0) }}}}</div>\n'
        f'{indent2}    {{% for h in leg.horses %}}{{{{ h.number }}}}. {{{{ h.name }}}}{{% if not loop.last %}}, {{% endif %}}{{% endfor %}}\n'
        f'{indent2}</div>\n'
        f'{indent2}{{% endfor %}}\n'
        f'{indent2}{{% endif %}}\n'
        f'\n'
    )

    lines[old_template_start:template_end_idx + 1] = [new_template]

    #
    # Patch 3: uppdatera render_page-kwargs - byt ut den gamla
    # kamt_v2_shadow=kamt_v2_shadow mot de tva nya variablerna.
    #
    idx3 = find_line_index(
        lines, "kamt_v2_shadow=kamt_v2_shadow,", "gamla render_page-kwarg-raden"
    )
    indent3 = leading_whitespace(lines[idx3])
    lines[idx3] = (
        f"{indent3}kamt_v2_shadow_legs=kamt_v2_shadow_legs,\n"
        f"{indent3}kamt_v2_shadow_cost=kamt_v2_shadow_cost,\n"
    )

    with open(APP_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("Patchat klart: KAMT v2 genererar nu ett fullstandigt skuggsystem.")


if __name__ == "__main__":
    main()
