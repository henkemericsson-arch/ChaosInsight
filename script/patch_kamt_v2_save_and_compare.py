"""
Engangsskript som:
1. Sparar KAMT v2:s skuggsystem via PredictionLogger (taggat
   strategy="kamt_v2"), sa det blir sokbart, visningsbart och
   utvarderingsbart precis som de riktiga systemen.
2. Lagger till en etikett for "kamt_v2" i strategy_labels i bade
   visa_spel() och strategier() - sjalva jamforelselogiken i
   strategier() ar redan helt generisk och behover ingen
   kodandring, bara en snyggare etikett istallet for raw-strangen
   "kamt_v2".

Hittar infogningspunkterna via textinnehall (inte exakt
whitespace), och skiljer visa_spel():s strategy_labels-block fran
strategier():s via vad som star strax efter (bada innehaller
"legacy": ..., som inte ensamt racker som ankare).

Kor fran projektroten:
    python script/patch_kamt_v2_save_and_compare.py
"""

import sys

APP_PATH = "web_app/app.py"

LEGACY_LINE_NEEDLE = '"legacy": "Gammal princip (fast gardering)",'


def find_all_indices(lines, needle):
    return [i for i, line in enumerate(lines) if needle in line]


def leading_whitespace(line):
    return line[:len(line) - len(line.lstrip())]


def find_line_index(lines, needle, label):
    matches = [i for i, line in enumerate(lines) if needle in line]
    if len(matches) != 1:
        print(f"AVBRUTET: hittade '{needle}' pa {len(matches)} rader for '{label}' (forvantade exakt 1).")
        print("Ingenting har andrats. Granska filen manuellt.")
        sys.exit(1)
    return matches[0]


def find_strategy_labels_block(lines, followed_by, label):
    #
    # Hittar den specifika strategy_labels = {...}-forekomst som
    # foljs (inom nagra rader efter "legacy"-raden) av en given,
    # unik markortext - sa att visa_spel():s och strategier():s
    # egna dictar kan skiljas at aven om bada innehaller samma
    # "legacy"-rad.
    #
    candidates = find_all_indices(lines, LEGACY_LINE_NEEDLE)
    matches = []

    for idx in candidates:
        window = "".join(lines[idx:idx + 8])
        if followed_by in window:
            matches.append(idx)

    if len(matches) != 1:
        print(f"AVBRUTET: hittade {len(matches)} strategy_labels-block for '{label}' (forvantade exakt 1).")
        print("Ingenting har andrats. Granska filen manuellt.")
        sys.exit(1)

    return matches[0]


def main():
    with open(APP_PATH, encoding="utf-8") as f:
        lines = f.readlines()

    #
    # Patch 1: spara KAMT v2:s skuggsystem via PredictionLogger,
    # direkt efter att kamt_v2_shadow_legs raknats fram - fortfarande
    # innanfor samma try/except som redan skyddar hela KAMT v2-
    # blocket fran att paverka det riktiga flodet.
    #
    idx1 = find_line_index(
        lines,
        'kamt_v2_leg_selections, key=lambda leg: leg["race"].race_number',
        "sorted(...)-raden for kamt_v2_shadow_legs",
    )
    # Nasta rad ar den avslutande ")" for sorted(...)-anropet.
    insert_after = idx1 + 1

    #
    # Indenteringen ska las av fran SJALVA SATSEN som paborjar
    # tilldelningen ("kamt_v2_shadow_legs = sorted("), inte fran
    # den har fortsattningsraden (som ligger ett steg djupare
    # eftersom den ar inuti sorted(...)-parenteserna) - annars blir
    # den infogade koden felaktigt indenterad.
    #
    stmt_idx = find_line_index(
        lines, "kamt_v2_shadow_legs = sorted(", "satsraden for kamt_v2_shadow_legs"
    )
    indent = leading_whitespace(lines[stmt_idx])

    save_block = (
        f'\n'
        f'{indent}if kamt_v2_shadow_legs:\n'
        f'{indent}    prediction_logger.save(\n'
        f'{indent}        game=analysis_data.game,\n'
        f'{indent}        leg_selections=kamt_v2_shadow_legs,\n'
        f'{indent}        total_cost=kamt_v2_shadow_cost,\n'
        f'{indent}        selection={{\n'
        f'{indent}            "max_cost": max_cost, "risk": risk,\n'
        f'{indent}            "spikes": spikes, "locks": locks,\n'
        f'{indent}        }},\n'
        f'{indent}        weather=analysis_data.weather,\n'
        f'{indent}        strategy="kamt_v2",\n'
        f'{indent}    )\n'
    )
    lines.insert(insert_after + 1, save_block)

    #
    # Patch 2: lagg till etikett i visa_spel():s strategy_labels -
    # den dict som foljs av "sibling = find_strategy_sibling".
    #
    idx2 = find_strategy_labels_block(
        lines, "sibling = find_strategy_sibling", "visa_spel()"
    )
    indent2 = leading_whitespace(lines[idx2])
    lines.insert(
        idx2 + 1,
        f'{indent2}"kamt_v2": "KAMT v2 (experimentell)",\n',
    )

    #
    # Patch 3: lagg till etikett i strategier():s strategy_labels -
    # den dict som foljs av "rows = []".
    #
    idx3 = find_strategy_labels_block(lines, "rows = []", "strategier()")
    indent3 = leading_whitespace(lines[idx3])
    lines.insert(
        idx3 + 1,
        f'{indent3}"kamt_v2": "KAMT v2 (experimentell)",\n',
    )

    with open(APP_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("Patchat klart: KAMT v2 sparas nu for utvardering och syns i jamforelsen.")


if __name__ == "__main__":
    main()
