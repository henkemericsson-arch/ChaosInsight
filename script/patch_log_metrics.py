import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#
# Etapp 2, steg 1: logga alla delmått (horse.metrics) och kodversion.
#   - services/db.py: kolumnerna metrics_json, code_version
#     (+ migrate_schema som lägger till dem i befintliga databaser)
#   - prediction_logger.py: sparar metrics och code_version (expert_index rörs inte)
#   - services/learning_engine.py: för över dem till observationerna
# Idempotent: kan köras flera gånger. Ändrar inget om ankartexten saknas
# (skriver då vad som måste göras för hand).
#
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
problems = []


def find(candidates):
    for rel in candidates:
        path = os.path.join(ROOT, rel)
        if os.path.exists(path):
            return path
    problems.append(f"Hittar ingen av: {', '.join(candidates)}")
    return None


def patch(path, label, marker, anchor, replacement):
    if path is None:
        return
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if marker in text:
        print(f"  {label}: redan patchad")
        return
    if text.count(anchor) != 1:
        problems.append(f"{label}: ankartexten hittades {text.count(anchor)} gånger i {path}")
        return
    text = text.replace(anchor, replacement)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  {label}: patchad")


db_py = find(["services/db.py"])
logger_py = find(["services/prediction_logger.py", "prediction_logger.py", "foundation/prediction_logger.py"])
engine_py = find(["services/learning_engine.py", "learning_engine.py"])

print("Patchar ...")

patch(db_py, "db: kolumnlista", '"metrics_json", "code_version"',
      '"chosen_by_system", "actual_finish_order", "actual_place",',
      '"metrics_json", "code_version",\n    "chosen_by_system", "actual_finish_order", "actual_place",')

patch(db_py, "db: schema", "metrics_json TEXT",
      "predicted_chaos_index REAL, predicted_expert_index REAL,",
      "predicted_chaos_index REAL, predicted_expert_index REAL,\n    metrics_json TEXT, code_version TEXT,")

patch(db_py, "db: migrate_schema", "def migrate_schema",
      "def init_db(db_path=None):",
      'def migrate_schema(conn):\n'
      '    #\n'
      '    # Lagger till kolumner som tillkommit efter att databasen skapades\n'
      '    # (CREATE TABLE IF NOT EXISTS andrar inte en befintlig tabell).\n'
      '    #\n'
      '    existing = {row[1] for row in conn.execute("PRAGMA table_info(observations)")}\n'
      '    for column in ("metrics_json", "code_version"):\n'
      '        if column not in existing:\n'
      '            conn.execute(f"ALTER TABLE observations ADD COLUMN {column} TEXT")\n'
      '    conn.commit()\n\n\n'
      'def init_db(db_path=None):')

patch(db_py, "db: init_db anropar migrate_schema", "migrate_schema(conn)\n",
      "    conn.executescript(SCHEMA)\n",
      "    conn.executescript(SCHEMA)\n    migrate_schema(conn)\n")

patch(logger_py, "logger: import", "from foundation.run_info import",
      "import json\n",
      "import json\nfrom foundation.run_info import code_version, metrics_to_dict\n")

patch(logger_py, "logger: record", '"code_version": code_version(),',
      '"saved_at": timestamp.isoformat(),',
      '"saved_at": timestamp.isoformat(),\n            "code_version": code_version(),')

patch(logger_py, "logger: hästmått", '"metrics": metrics_to_dict(horse.metrics),',
      '"chosen": horse.number in chosen_numbers,',
      '"metrics": metrics_to_dict(horse.metrics),\n'
      '                    "chosen": horse.number in chosen_numbers,')

patch(engine_py, "engine: import", "from foundation.run_info import",
      "import json\n",
      "import json\nfrom foundation.run_info import dump_metrics\n")

patch(engine_py, "engine: observation", '"metrics_json": dump_metrics(',
      '"predicted_expert_index": horse.get("expert_index"),',
      '"predicted_expert_index": horse.get("expert_index"),\n'
      '                "metrics_json": dump_metrics(horse.get("metrics")),\n'
      '                "code_version": prediction.get("code_version"),')

if problems:
    print("\nKräver handpåläggning:")
    for p in problems:
        print("  -", p)
    sys.exit(1)

# Migrera den riktiga databasen direkt, så att kolumnerna finns även
# innan appen startats om.
from services.db import init_db
init_db().close()
print("Databasen migrerad (metrics_json, code_version).")
