"""
Engangsskript som lagger till en ny sida, /kamt-jamforelse, som
jamfor KAMT v1 och KAMT v2 lopp for lopp for spel dar bada finns
sparade och avgjorda - raknar hur ofta bara den ena, bada, eller
ingendera traffade ratt vinnare.

Ren tillaggslogik - rör inga befintliga rutter eller sparad data,
bara lasning av redan befintliga utvarderingsfiler.

Hittar infogningspunkterna via textinnehall, inte exakt whitespace.

Kor fran projektroten:
    python script/patch_kamt_jamforelse.py
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


ROUTE_CODE = '''@app.route("/kamt-jamforelse")
def kamt_jamforelse():
    #
    # Jamfor KAMT v1 (continuous/legacy) och KAMT v2 lopp for lopp,
    # for spel dar bada finns sparade och avgjorda - visar hur ofta
    # bara den ena, bada, eller ingendera traffade ratt vinnare i
    # samma lopp. Rent lasande - paverkar ingen sparad data.
    #
    games = {}

    if os.path.isdir(PREDICTIONS_DIR):
        for filename in os.listdir(PREDICTIONS_DIR):
            if not filename.endswith(".json"):
                continue

            path = os.path.join(PREDICTIONS_DIR, filename)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            outcome = data.get("outcome")
            if not outcome:
                continue

            game_id = data.get("game_id")
            strategy = data.get("strategy")
            if not game_id or not strategy:
                continue

            entry = games.setdefault(game_id, {
                "spel": data.get("spel", "?"),
                "track": data.get("track", "?"),
                "date": data.get("date", "?"),
                "v1": None,
                "v2": None,
            })

            if strategy == "kamt_v2":
                entry["v2"] = outcome
            elif strategy in ("continuous", "legacy"):
                #
                # Foredra "continuous" om bada finns for samma spel -
                # det ar den aktiva principen, "legacy" ar mest en
                # historisk jamforelsepunkt.
                #
                if entry["v1"] is None or strategy == "continuous":
                    entry["v1"] = outcome

    only_v1 = 0
    only_v2 = 0
    both_hit = 0
    both_miss = 0
    game_rows = []

    for game_id, entry in games.items():
        if entry["v1"] is None or entry["v2"] is None:
            continue

        v1_hits_by_race = {
            leg["race_number"]: leg["hit"]
            for leg in entry["v1"]["legs"]
            if leg["status"] == "avgjort"
        }
        v2_hits_by_race = {
            leg["race_number"]: leg["hit"]
            for leg in entry["v2"]["legs"]
            if leg["status"] == "avgjort"
        }

        common_races = sorted(set(v1_hits_by_race) & set(v2_hits_by_race))
        if not common_races:
            continue

        game_only_v1 = 0
        game_only_v2 = 0
        game_both_hit = 0
        game_both_miss = 0

        for race_number in common_races:
            v1_hit = v1_hits_by_race[race_number]
            v2_hit = v2_hits_by_race[race_number]

            if v1_hit and v2_hit:
                both_hit += 1
                game_both_hit += 1
            elif v1_hit and not v2_hit:
                only_v1 += 1
                game_only_v1 += 1
            elif v2_hit and not v1_hit:
                only_v2 += 1
                game_only_v2 += 1
            else:
                both_miss += 1
                game_both_miss += 1

        game_rows.append({
            "spel": entry["spel"],
            "track": entry["track"],
            "date": entry["date"],
            "legs_compared": len(common_races),
            "only_v1": game_only_v1,
            "only_v2": game_only_v2,
            "both_hit": game_both_hit,
            "both_miss": game_both_miss,
        })

    total_legs = only_v1 + only_v2 + both_hit + both_miss

    return render_page("""
        <h1>KAMT v1 vs KAMT v2</h1>
        <p style="color:#8b949e; font-size:0.9rem;">
            Jamfor lopp for lopp - bara for spel dar bada systemen ar sparade och avgjorda.
        </p>

        {% if total_legs == 0 %}
        <p>Inga jamforbara lopp hittades an - generera och utvardera samma spel med bade KAMT v1 och KAMT v2 for att bygga underlag.</p>
        {% else %}
        <div class="card leg">
            <b>Totalt {{ total_legs }} jamforda lopp</b>
            <div>Bara KAMT v1 traffade: {{ only_v1 }} ({{ "%.1f"|format(100*only_v1/total_legs) }}%)</div>
            <div>Bara KAMT v2 traffade: {{ only_v2 }} ({{ "%.1f"|format(100*only_v2/total_legs) }}%)</div>
            <div>Bada traffade: {{ both_hit }} ({{ "%.1f"|format(100*both_hit/total_legs) }}%)</div>
            <div>Bada missade: {{ both_miss }} ({{ "%.1f"|format(100*both_miss/total_legs) }}%)</div>
        </div>

        <h2>Per spel</h2>
        {% for row in game_rows %}
        <div class="card leg">
            <b>{{ row.spel }} - {{ row.track }} - {{ row.date }}</b>
            <div>{{ row.legs_compared }} jamforda lopp</div>
            <div>Bara v1: {{ row.only_v1 }} | Bara v2: {{ row.only_v2 }} | Bada traff: {{ row.both_hit }} | Bada miss: {{ row.both_miss }}</div>
        </div>
        {% endfor %}
        {% endif %}

        <a class="footer-link" href="/">Hem</a>
    """, only_v1=only_v1, only_v2=only_v2, both_hit=both_hit, both_miss=both_miss,
        total_legs=total_legs, game_rows=game_rows)


'''


def main():
    with open(APP_PATH, encoding="utf-8") as f:
        lines = f.readlines()

    #
    # Patch 1: infoga den nya rutten strax fore /strategier-rutten.
    #
    idx1 = find_line_index(lines, '@app.route("/strategier")', "strategier-ruttens start")
    indent = leading_whitespace(lines[idx1])

    route_lines = [f"{indent}{line}" if line.strip() else line for line in ROUTE_CODE.splitlines(keepends=True)]
    lines[idx1:idx1] = route_lines

    #
    # Patch 2: lagg till en lank till den nya sidan pa startsidan,
    # strax efter den befintliga lanken till /strategier.
    #
    idx2 = find_line_index(
        lines,
        '<a class="footer-link" href="/strategier">Strategijämförelse</a>',
        "startsidans lank till /strategier",
    )
    indent2 = leading_whitespace(lines[idx2])
    lines.insert(
        idx2 + 1,
        f'{indent2}<a class="footer-link" href="/kamt-jamforelse">KAMT v1 vs v2</a>\n',
    )

    with open(APP_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("Patchat klart: /kamt-jamforelse tillagd, lank pa startsidan tillagd.")


if __name__ == "__main__":
    main()
