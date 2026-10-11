#
# Lägger till DatabaseManager.observations_for_analysis() i
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
    def observations_for_analysis(self):
        #
        # Alla observationsrader som dicts, för Learning Engines
        # analysmoduler (learning/). Ren läsning - ingen filtrering
        # eller tolkning sker här, det görs i analyslagret.
        #
        cursor = self._conn.execute("SELECT * FROM observations")
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
'''

MARKER = "observations_for_analysis"


def main():
    with open(PATH, encoding="utf-8") as f:
        source = f.read()

    if MARKER in source:
        print("Redan patchad - ingen ändring.")
        return

    lines = source.split("\n")

    #
    # Infoga efter rubrikblocket "Lasvagar" (rubriktext + avslutande
    # streckrad). Faller tillbaka på att infoga före commit().
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
