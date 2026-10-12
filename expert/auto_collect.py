import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from config import expert_sources
from expert.collector import ExpertCollector
from expert.fetcher import Fetcher
from expert.interpreter import Interpreter
from expert.trav import lexicon
from foundation.database_manager import DatabaseManager

#
# Automatisk insamling av experttips (Data Collector-steget) for ett spel.
# Anropas nar ett spel ska analyseras. Hamtningen sker i bakgrunden sa att
# sidan inte vantar (varje sajt far en artig paus mellan anrop). Tipsen
# anvands av ExpertAnalyzer nasta gang spelet analyseras.
#
# Hamtar inte om spelet hamtats nyligen (MAX_AGE_HOURS) och inte for spel
# som redan gatt (datum fore idag). Ett pagaende jobb startas aldrig dubbelt.
#

MAX_AGE_HOURS = 6
LOCAL_TZ = ZoneInfo("Europe/Stockholm")

_running = set()
_lock = threading.Lock()


def build_roster(races):
    # Loppnummer = position i spelet (1..N), samma som ExpertAnalyzer anvander.
    return {
        leg: {horse.number: horse.name for horse in race.horses}
        for leg, race in enumerate(races, start=1)
    }


def _recently_collected(db, game_id, now):
    articles = db.expert_articles_for_game(game_id)
    if not articles:
        return False
    newest = max(a["fetched_at"] for a in articles)
    try:
        fetched = datetime.fromisoformat(newest)
    except ValueError:
        return False
    return now - fetched < timedelta(hours=MAX_AGE_HOURS)


def collect_now(game_id, game_date, track, roster, db=None, fetcher=None, sources=None):
    # Synkron insamling. Returnerar rapporterna. Anvands av bakgrundstradden.
    own_db = db is None
    db = db or DatabaseManager()
    try:
        collector = ExpertCollector(
            fetcher=fetcher or Fetcher(),
            interpreter=Interpreter(lexicon),
            db=db,
            sources=sources if sources is not None else expert_sources.SOURCES,
            manual_articles=expert_sources.MANUAL_ARTICLES,
        )
        return collector.collect(game_id, game_date, track, roster)
    finally:
        if own_db:
            db.close()


def start_expert_collection(game_id, game_date, races, now=None, runner=None, spawn=None):
    # Returnerar True om en insamling startades. runner/spawn kan bytas i test.
    now = now or datetime.now(timezone.utc)
    if not races or not game_date:
        return False
    if str(game_date)[:10] < now.astimezone(LOCAL_TZ).date().isoformat():
        return False

    with _lock:
        if game_id in _running:
            return False
        db = DatabaseManager()
        try:
            if _recently_collected(db, game_id, now):
                return False
        finally:
            db.close()
        _running.add(game_id)

    roster = build_roster(races)
    track = races[0].track
    run = runner or collect_now

    def job():
        try:
            reports = run(game_id, game_date, track, roster)
            ok = sum(1 for r in (reports or []) if r.get("status") == "ok")
            print(f"[Expert] Insamling klar for {game_id}: {ok} artikel/artiklar tolkade.")
        except Exception as exc:
            print(f"[Expert] Insamling misslyckades for {game_id}: {exc!r}")
        finally:
            with _lock:
                _running.discard(game_id)

    (spawn or (lambda fn: threading.Thread(target=fn, daemon=True).start()))(job)
    return True
