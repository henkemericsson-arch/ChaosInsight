import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

#
# Experttips (006_Expert_Module_Design.md), idempotent:
#   services/db.py                 tabellerna expert_tips, expert_articles
#   foundation/database_manager.py insert_/lasmetoder (enda vagen till SQL)
#   analysis/register_modules.py   registrerar ExpertAnalyzer fore CrowdEngine
#   web_app/app.py                 tar bort den gamla direktanvandningen av
#                                  analysis/expert_analyzer.py
# Ändrar ingenting om en ankartext saknas - skriver da vad som maste goras
# for hand.
#
problems = []


def read(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        problems.append(f"{rel}: filen finns inte")
        return None, path
    with open(path, encoding="utf-8") as f:
        return f.read(), path


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def replace_once(text, label, marker, anchor, replacement):
    if text is None:
        return text
    if marker in text:
        print(f"  {label}: redan patchad")
        return text
    if text.count(anchor) != 1:
        problems.append(f"{label}: ankartexten hittades {text.count(anchor)} gånger")
        return text
    print(f"  {label}: patchad")
    return text.replace(anchor, replacement)


print("Patchar ...")

# ---- services/db.py ---------------------------------------------------
text, path = read("services/db.py")
orig = text

text = replace_once(
    text, "db: kolumnlistor", "EXPERT_TIP_COLUMNS",
    "\nSCHEMA = \"\"\"",
    '''
EXPERT_TIP_COLUMNS = [
    "fetched_at", "game_id", "date", "source", "article_url", "leg",
    "horse_number", "horse_name", "signal", "rank", "rank_of", "confidence",
]

EXPERT_ARTICLE_COLUMNS = [
    "fetched_at", "game_id", "source", "article_url", "lines",
    "legs_in_roster", "legs_with_tips", "tips", "unlinked_cues",
]

SCHEMA = """''')

text = replace_once(
    text, "db: tabeller", "CREATE TABLE IF NOT EXISTS expert_tips",
    '"""\n\n\ndef get_connection',
    '''
CREATE TABLE IF NOT EXISTS expert_tips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at TEXT, game_id TEXT, date TEXT, source TEXT,
    article_url TEXT, leg INTEGER, horse_number INTEGER,
    horse_name TEXT, signal TEXT, rank INTEGER, rank_of INTEGER,
    confidence REAL,
    UNIQUE(fetched_at, game_id, source, leg, horse_number, signal)
);

CREATE INDEX IF NOT EXISTS idx_expert_tips_game
    ON expert_tips(game_id, source);

CREATE TABLE IF NOT EXISTS expert_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at TEXT, game_id TEXT, source TEXT, article_url TEXT,
    lines INTEGER, legs_in_roster INTEGER, legs_with_tips INTEGER,
    tips INTEGER, unlinked_cues INTEGER,
    UNIQUE(fetched_at, game_id, source, article_url)
);
"""


def get_connection''')
if text is not None and text != orig:
    write(path, text)

# ---- foundation/database_manager.py --------------------------------------
text, path = read("foundation/database_manager.py")
orig = text

text = replace_once(
    text, "manager: import", "EXPERT_TIP_COLUMNS,",
    "    KAMT_V2_FORECAST_COLUMNS,\n)",
    "    KAMT_V2_FORECAST_COLUMNS,\n    EXPERT_TIP_COLUMNS,\n    EXPERT_ARTICLE_COLUMNS,\n)")

text = replace_once(
    text, "manager: metoder", "def insert_expert_tip",
    "    # ------------------------------------------------------------\n    # Lasvagar",
    '''    def insert_expert_tip(self, row, or_ignore=True):
        #
        # Tolkad uppgift fran en expertkalla (expert/collector.py).
        #
        insert_row(self._conn, "expert_tips", row, EXPERT_TIP_COLUMNS, or_ignore=or_ignore)

    def insert_expert_article(self, row, or_ignore=True):
        #
        # Tolkningstackning per hamtad artikel (hur mycket forstods).
        #
        insert_row(self._conn, "expert_articles", row, EXPERT_ARTICLE_COLUMNS, or_ignore=or_ignore)

    def expert_tips_for_game(self, game_id, until=None):
        #
        # Alla lagrade experttips for ett spel (som dicts). `until` (ISO-
        # tid) begransar till hamtningar fore den tidpunkten, sa att en
        # analys i efterhand inte ser tips som kom senare. Ren lasning.
        #
        sql = "SELECT * FROM expert_tips WHERE game_id = ?"
        params = [game_id]
        if until is not None:
            sql += " AND fetched_at <= ?"
            params.append(until)
        cursor = self._conn.execute(sql, params)
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def expert_articles_for_game(self, game_id):
        cursor = self._conn.execute(
            "SELECT * FROM expert_articles WHERE game_id = ? ORDER BY fetched_at", (game_id,)
        )
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    # ------------------------------------------------------------
    # Lasvagar''')
if text is not None and text != orig:
    write(path, text)

# ---- analysis/register_modules.py ----------------------------------------
text, path = read("analysis/register_modules.py")
orig = text
text = replace_once(
    text, "register: import", "from analysis.modules.expert_analyzer import ExpertAnalyzer",
    "from analysis.crowd_engine import CrowdEngine\n",
    "from analysis.modules.expert_analyzer import ExpertAnalyzer\nfrom analysis.crowd_engine import CrowdEngine\n")
text = replace_once(
    text, "register: modul", "ExpertAnalyzer())",
    "    engine.add_module(CrowdEngine())",
    "    engine.add_module(ExpertAnalyzer())\n    engine.add_module(CrowdEngine())")
if text is not None and text != orig:
    write(path, text)

# ---- web_app/app.py -------------------------------------------------------
text, path = read("web_app/app.py")
orig = text
text = replace_once(
    text, "app: import", "# expert: se analysis/modules/expert_analyzer.py",
    "from analysis.expert_analyzer import ExpertAnalyzer\n",
    "# expert: se analysis/modules/expert_analyzer.py (registreras i register_modules)\n")
text = replace_once(
    text, "app: instans", "# expert-instans borttagen",
    "    expert_analyzer = ExpertAnalyzer()\n",
    "    # expert-instans borttagen: experttips samlas av expert/collector.py\n")
text = replace_once(
    text, "app: insamling", "# expert-insamling borttagen",
    "    expert_tips = expert_analyzer.collect_tips(analysis_data.game.id)\n\n",
    "    # expert-insamling borttagen (script/collect_expert_tips.py)\n\n")
text = replace_once(
    text, "app: apply", "# expert-apply borttagen",
    "        expert_analyzer.apply(race, leg_index, expert_tips)\n",
    "        # expert-apply borttagen: ExpertAnalyzer kors i Analysis Engine\n")
if text is not None and text != orig:
    write(path, text)

# ---- web_app/app.py: automatisk insamling ----------------------------------
text, path = read("web_app/app.py")
orig = text
text = replace_once(
    text, "app: auto-import", "from expert.auto_collect import start_expert_collection",
    "from analysis.register_modules import register_modules\n",
    "from analysis.register_modules import register_modules\nfrom expert.auto_collect import start_expert_collection\n")
text = replace_once(
    text, "app: auto-start", "start_expert_collection(game.id",
    "    analysis_data = collector.collect(game)\n",
    "    analysis_data = collector.collect(game)\n\n"
    "    # Data Collector: experttips hamtas i bakgrunden (expert/auto_collect.py)\n"
    "    start_expert_collection(game.id, game.date, analysis_data.races)\n")
if text is not None and text != orig:
    write(path, text)

if problems:
    print("\nKräver handpåläggning:")
    for p in problems:
        print("  -", p)
    sys.exit(1)

from foundation.database_manager import DatabaseManager
DatabaseManager().close()
print("Databasen migrerad (expert_tips, expert_articles).")
