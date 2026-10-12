#
# Etapp 4 (005 avsnitt 18). Idempotent: kan köras flera gånger.
# Körs från projektroten:  python script/patch_tuning.py
#
# Ändrar:
#   services/db.py                  tabellerna tuning_state och tuning_log
#   foundation/database_manager.py  läs-/skrivmetoder för dem
#   learning/trav/settings.py       trösklar för justering och återrullning
#
# Allt eller inget: om något ankare inte hittas skrivs ingen fil.
#
import sys

edits = {}
problems = []


def load(path):
    if path not in edits:
        with open(path, encoding="utf-8") as f:
            edits[path] = f.read()
    return edits[path]


def edit(path, label, marker, old, new):
    text = load(path)
    if marker in text:
        print(f"  {label}: redan gjort")
        return
    count = text.count(old)
    if count != 1:
        print(f"  {label}: KRÄVER HANDPÅLÄGGNING (ankare hittades {count} gånger)")
        problems.append((path, label))
        return
    edits[path] = text.replace(old, new, 1)
    print(f"  {label}: patchad")


print("Patchar etapp 4 ...")

P = "services/db.py"
edit(P, "db: kolumnlista", "TUNING_LOG_COLUMNS",
     'SCHEMA = """\n',
     'TUNING_LOG_COLUMNS = ["logged_at", "action", "version", "reason", "evidence"]\n\n'
     'SCHEMA = """\n')
edit(P, "db: tabeller", "CREATE TABLE IF NOT EXISTS tuning_log",
     "    params TEXT, reason TEXT, evidence TEXT\n);\n\"\"\"",
     "    params TEXT, reason TEXT, evidence TEXT\n);\n\n"
     "CREATE TABLE IF NOT EXISTS tuning_state (\n"
     "    key TEXT PRIMARY KEY, value TEXT, updated_at TEXT\n"
     ");\n\n"
     "CREATE TABLE IF NOT EXISTS tuning_log (\n"
     "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
     "    logged_at TEXT, action TEXT, version INTEGER, reason TEXT, evidence TEXT\n"
     ");\n\"\"\"")

P = "foundation/database_manager.py"
edit(P, "manager: import", "    TUNING_LOG_COLUMNS,\n",
     "    PARAMETER_SET_COLUMNS,\n)",
     "    PARAMETER_SET_COLUMNS,\n    TUNING_LOG_COLUMNS,\n)")
edit(P, "manager: metoder", "def tuning_state_get",
     "    # ------------------------------------------------------------\n    # Lasvagar - flyttade",
     '''    # ------------------------------------------------------------
    # Automatisk justering (Learning Engine etapp 4): tillstand och logg
    # ------------------------------------------------------------

    def tuning_state_get(self, key):
        row = self._conn.execute(
            "SELECT value FROM tuning_state WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else None

    def tuning_state_set(self, key, value, updated_at):
        self._conn.execute(
            "INSERT OR REPLACE INTO tuning_state (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, updated_at),
        )
        self._conn.commit()

    def insert_tuning_log(self, row):
        insert_row(self._conn, "tuning_log", row, TUNING_LOG_COLUMNS)

    def tuning_log_entries(self, limit=20):
        cursor = self._conn.execute(
            "SELECT * FROM tuning_log ORDER BY id DESC LIMIT ?", (limit,)
        )
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    # ------------------------------------------------------------
    # Lasvagar - flyttade''')

P = "learning/trav/settings.py"
edit(P, "settings: trösklar", "TUNING_DAMPING",
     "MIN_RACES_FOR_TUNING = 300\n",
     """MIN_RACES_FOR_TUNING = 300

#
# Automatisk justering (etapp 4, 005 avsnitt 5 och 18).
# TUNING_MIN_NEW_RACES   nya lopp sedan senaste justering (avkylning)
# TUNING_DAMPING         η: ny = gammal + η * (föreslagen - gammal)
# TUNING_STEP_CAP        högsta relativa ändring per justering
# TUNING_TOTAL_CAP       högsta relativa avstånd från baseline
# ROLLBACK_MIN_RACES     lopp med ny version innan återrullning prövas
# ROLLBACK_WINDOW        högst så många lopp räknas i uppföljningen
#
TUNING_MIN_NEW_RACES = 100
TUNING_DAMPING = 0.2
TUNING_STEP_CAP = 0.10
TUNING_TOTAL_CAP = 0.50
ROLLBACK_MIN_RACES = 50
ROLLBACK_WINDOW = 100
""")

if problems:
    print()
    print("Inget ändrades. Skicka utskriften ovan så justeras patchen.")
    sys.exit(1)

for path, text in edits.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
print("Klart.")
