#
# Lägger till DatabaseManager.iter_backfill_legs() i
# foundation/database_manager.py. Idempotent: kör man den två gånger
# händer ingenting andra gången. Ändrar inget annat i filen.
#
import os
import sys

PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "foundation", "database_manager.py",
)

METHOD = '''
    def iter_backfill_legs(self):
        #
        # Historiska starter (backfill_starts) grupperade per lopp i
        # kronologisk ordning (datum, spel, loppnummer). Generator - hela
        # tabellen läses aldrig in i minnet. Ger (nyckel, [startposter]).
        #
        cursor = self._conn.execute(
            "SELECT date, game_id, race_number, track, horse_name, odds, "
            "actual_place, actual_finish_order, actual_scratched "
            "FROM backfill_starts ORDER BY date, game_id, race_number"
        )
        columns = [c[0] for c in cursor.description]

        current_key = None
        current = []
        for row in cursor:
            record = dict(zip(columns, row))
            key = (record["date"], record["game_id"], record["race_number"])
            if key != current_key:
                if current:
                    yield current_key, current
                current_key = key
                current = []
            current.append(record)

        if current:
            yield current_key, current
'''

MARKER = "iter_backfill_legs"


def main():
    with open(PATH, encoding="utf-8") as f:
        source = f.read()

    if MARKER in source:
        print("Redan patchad - ingen ändring.")
        return

    lines = source.split("\n")

    #
    # Infoga efter rubrikblocket "Lasvagar". Faller tillbaka på att
    # infoga före commit().
    #
    insert_at = None
    for i, line in enumerate(lines):
        if line.strip().startswith("# Lasvagar") and i + 1 < len(lines):
            insert_at = i + 2
            break

    if insert_at is None:
        for i, line in enumerate(lines):
            if line.startswith("    def commit(self):"):
                insert_at = i
                break

    if insert_at is None:
        print("Hittade ingen infogningspunkt - ändrar inget.")
        sys.exit(1)

    new_lines = lines[:insert_at] + METHOD.split("\n") + lines[insert_at:]

    with open(PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))

    print(f"Patchade {PATH}")


if __name__ == "__main__":
    main()
