"""
Engangsskript som patchar web_app/app.py och kopplar in KAMT v2:s
skuggade/parallella lage i /resultat-rutten - utan att paverka
vilka hastar som faktiskt valjs i det riktiga systemet.

Hittar infogningspunkterna via textinnehall (inte exakt
whitespace/indentering), och laser av ratt indentering fran
respektive rad automatiskt - robust aven om texten kopierats
genom ett granssnitt som kan ha andrat radbrytningar.

Om nagon av ankarraderna inte hittas exakt en gang avbryts
skriptet utan att andra nagot.

Kor fran projektroten:
    python script/patch_kamt_v2_shadow.py
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
    # Patch 1: infoga KAMT v2-skugglogik direkt EFTER
    # "xpress = _detect_xpress(race.track for race in
    # analysis_data.races)"-raden - det exakta uttrycket
    # forekommer bara i /resultat (andra stallen i appen anropar
    # _detect_xpress med andra variabelnamn), sa det ar en saker,
    # unik ankarpunkt aven om "strategy_labels = {" inte ar det.
    #
    idx1 = find_line_index(
        lines,
        "xpress = _detect_xpress(race.track for race in analysis_data.races)",
        "xpress-raden i /resultat",
    )
    indent = leading_whitespace(lines[idx1])

    shadow_block = (
        f'\n'
        f'{indent}#\n'
        f'{indent}# KAMT v2 (skuggat/parallellt lage, experimentellt) - kors\n'
        f'{indent}# och loggas for framtida utvardering, men paverkar ALDRIG\n'
        f'{indent}# vilka hastar som faktiskt valjs i systemet ovan. Om nagot\n'
        f'{indent}# gar fel har ska det aldrig stoppa den riktiga\n'
        f'{indent}# systemgenereringen.\n'
        f'{indent}#\n'
        f'{indent}kamt_v2_shadow = []\n'
        f'{indent}try:\n'
        f'{indent}    from kamt_v2_forecast_logger import KamtV2ForecastLogger\n'
        f'\n'
        f'{indent}    kamt_v2_logger = KamtV2ForecastLogger()\n'
        f'{indent}    kamt_v2_predictions = kamt_v2_logger.log_game(\n'
        f'{indent}        analysis_data.races, game_id=analysis_data.game.id,\n'
        f'{indent}        weather=analysis_data.weather,\n'
        f'{indent}    )\n'
        f'\n'
        f'{indent}    for race in analysis_data.races:\n'
        f'{indent}        probabilities = kamt_v2_predictions.get(race.race_number)\n'
        f'{indent}        if not probabilities:\n'
        f'{indent}            continue\n'
        f'\n'
        f'{indent}        top = KamtV2ForecastLogger.top_pick(probabilities)\n'
        f'{indent}        if top is None:\n'
        f'{indent}            continue\n'
        f'\n'
        f'{indent}        horse_number, probability = top\n'
        f'{indent}        horse_name = next(\n'
        f'{indent}            (h.name for h in race.horses if h.number == horse_number),\n'
        f'{indent}            "?",\n'
        f'{indent}        )\n'
        f'{indent}        kamt_v2_shadow.append({{\n'
        f'{indent}            "race_number": race.race_number,\n'
        f'{indent}            "horse_number": horse_number,\n'
        f'{indent}            "horse_name": horse_name,\n'
        f'{indent}            "probability": probability,\n'
        f'{indent}        }})\n'
        f'\n'
        f'{indent}    kamt_v2_shadow.sort(key=lambda pick: pick["race_number"])\n'
        f'{indent}except Exception as exc:\n'
        f'{indent}    print(f"[KAMT v2 skugglage] Fel (paverkar inte riktiga systemet): {{exc}}")\n'
    )
    lines.insert(idx1 + 1, shadow_block)

    #
    # Patch 2: infoga mallblock fore
    # "{% if results|length > 1 %}"-raden i sjalva HTML-mallen.
    #
    idx2 = find_line_index(lines, "{% if results|length > 1 %}", "resultatjamforelse-mallraden")
    indent2 = leading_whitespace(lines[idx2])

    template_block = (
        f'{indent2}{{% if kamt_v2_shadow %}}\n'
        f'{indent2}<h2>KAMT v2 (experimentell, skuggad)</h2>\n'
        f'{indent2}<p style="color:#8b949e; font-size:0.85rem;">\n'
        f'{indent2}    Kor parallellt for utvardering - paverkar inte systemet ovan.\n'
        f'{indent2}</p>\n'
        f'{indent2}{{% for pick in kamt_v2_shadow %}}\n'
        f'{indent2}<div class="card leg">\n'
        f'{indent2}    <b>V{{{{ pick.race_number }}}}</b>\n'
        f'{indent2}    <div>{{{{ pick.horse_number }}}}. {{{{ pick.horse_name }}}} ({{{{ pick.probability }}}}%)</div>\n'
        f'{indent2}</div>\n'
        f'{indent2}{{% endfor %}}\n'
        f'{indent2}{{% endif %}}\n'
        f'\n'
    )
    lines.insert(idx2, template_block)

    #
    # Patch 3: lagg till kamt_v2_shadow=kamt_v2_shadow som en
    # extra kwarg till render_page-anropet.
    #
    idx3 = find_line_index(
        lines,
        "results=results, strategy_labels=strategy_labels, game_name=game_name,",
        "render_page-kwargs-raden",
    )
    indent3 = leading_whitespace(lines[idx3])
    lines.insert(idx3 + 1, f"{indent3}kamt_v2_shadow=kamt_v2_shadow,\n")

    with open(APP_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("Patchat klart: KAMT v2 skugglage inkopplat i /resultat.")


if __name__ == "__main__":
    main()
