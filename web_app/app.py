import sys
import os
import json
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask, request, redirect, url_for, render_template_string, jsonify, Response

from services.race_collector import RaceCollector
from services.analysis_data_collector import AnalysisDataCollector
from services.score_engine import ScoreEngine
from services.system_generator import SystemGenerator
from services.prediction_logger import PredictionLogger
from services.learning_engine import LearningEngine

from analysis.analysis_engine import AnalysisEngine
from analysis.register_modules import register_modules
from analysis.crowd_engine import CrowdEngine
from analysis.chaos_engine import ChaosEngine
from analysis.expert_analyzer import ExpertAnalyzer

from config.bet_types import SYSTEM_BET_TYPES
from models.game import Game

from script.backfill_history import run_backfill, load_progress, should_run_backfill

app = Flask(__name__)
race_collector = RaceCollector()

PREDICTIONS_DIR = "data/races"

#
# Enda historiska loppet som ar tillatet att generera nya system
# pa, for laborering/testning av funktioner. Alla andra redan
# avgjorda lopp blockeras fran nygenerering (se /installningar),
# eftersom ATG:s odds/rankingdata for avgjorda lopp kan andras i
# efterhand (livemedia, stallbacksrykten m.m.) och da gor
# testresultat missvisande.
#
DEMO_GAME_ID = "V86_2026-08-12_32_3"


def _is_historical_date(date_str):
    if not date_str:
        return False
    try:
        race_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return False
    return race_date < datetime.now().date()


#
# PWA-ikonerna serveras som riktiga filer i web_app/static/ (se
# manifest.json nedan) istallet for inbaddade som base64-text -
# de nya ikonerna ar for stora for att vara lampliga att badda in
# direkt i kallkoden.
#

MANIFEST_JSON = {
    "name": "Chaos Insight",
    "short_name": "ChaosInsight",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#000000",
    "theme_color": "#000000",
    "icons": [
        {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
    ],
}


@app.route("/manifest.json")
def manifest():
    return jsonify(MANIFEST_JSON)


@app.route("/service-worker.js")
def service_worker():
    #
    # Minimal service worker - kravs av Chrome for att "Lagg till pa
    # startskarmen" ska ge en riktig app-liknande upplevelse
    # (fullskarm, egen ikon). Gor ingen egen cachning - allt gar
    # fortfarande direkt mot den lokala Flask-servern.
    #
    body = "self.addEventListener('fetch', function() {});"
    return Response(body, mimetype="application/javascript")



PAGE_HEAD = """<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<meta name="theme-color" content="#000000">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Chaos Insight">
<link rel="manifest" href="/manifest.json">
<link rel="apple-touch-icon" href="/static/icon-192.png">
<link rel="icon" href="/static/icon-192.png">
<title>Chaos Insight</title>
<style>
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; width: 100%;
    background:#000000; color:#e6edf3;
    font-family: -apple-system, Roboto, Helvetica, Arial, sans-serif;
  }
  body {
    max-width: 520px; margin: 0 auto;
    padding: 16px 16px calc(env(safe-area-inset-bottom, 0px) + 24px);
  }
  h1 { color:#58a6ff; font-size: 1.5rem; margin: 8px 0 16px; }
  h2 { color:#58a6ff; font-size: 1.15rem; margin: 24px 0 10px; }
  p { line-height: 1.4; }
  a { color:#58a6ff; text-decoration:none; }
  form { display:flex; flex-direction:column; gap:12px; }
  label { font-size: 0.9rem; color:#8b949e; }
  input, select, button {
    width: 100%;
    padding: 14px; font-size: 16px; border-radius: 8px;
    border:1px solid #30363d; background:#161b22; color:#e6edf3;
  }
  select { -webkit-appearance: none; appearance: none; }
  button {
    background:#07e2f8; color:#04141a; border:none;
    font-weight:bold; cursor:pointer;
    min-height: 48px;
  }
  button:active { background:#3aeeff; }
  button:disabled { background:#30363d; color:#6e7681; cursor:not-allowed; }
  .card {
    background:#161b22; border:1px solid #30363d; border-radius:10px;
    padding:14px; margin-bottom:12px; display:block;
  }
  .card:active { border-color:#58a6ff; }
  .leg { margin-bottom:14px; }
  .kaos { color:#f0883e; font-size:14px; margin: 4px 0; }
  .footer-link {
    display:block; margin-top:24px; padding: 12px 0;
    text-align:center; font-weight:bold;
  }
  .btn-row { display:flex; gap:10px; }
  .btn-row button { flex:1; }
  .hit { color:#3fb950; margin-top: 6px; }
  .miss { color:#f85149; margin-top: 6px; }
  .undecided { color:#8b949e; margin-top: 6px; }

  @media print {
    html, body { background:#fff; color:#000; max-width:100%; }
    .no-print { display:none !important; }
    .card { background:#fff; border:1px solid #000; }
    a { color:#000; }
    h1, h2 { color:#000; }
    .kaos { color:#000; }
    .hit, .miss, .undecided { color:#000; }
    input, select, button { display:none; }
    .print-only { display:block !important; }
  }
  .print-only { display:none; }
  .brand-header { text-align:center; padding-top:2px; margin-bottom:4px; }
  .brand-header img { max-width:200px; width:55%; height:auto; }
  .brand-seal {
    position:fixed; top:50%; left:50%;
    transform:translate(-50%, -50%);
    width:70%; max-width:520px;
    opacity:0.10; z-index:-1;
  }
</style>
</head>
<body>
<div class="no-print brand-header">
  <img src="{{ url_for('static', filename='brand-dark.jpg') }}" alt="ChaosInsight">
</div>
"""

PAGE_FOOT = """
<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js').catch(function() {});
  }
</script>
</body>
</html>
"""


def render_page(body_template, **context):
    return render_template_string(PAGE_HEAD + body_template + PAGE_FOOT, **context)


def _format_local_time(raw_saved_at):
    #
    # saved_at sparas alltid i UTC (datetime.now(timezone.utc)) -
    # konvertera till svensk lokal tid innan visning, sa att
    # sommar-/vintertid hanteras automatiskt. Delad av
    # list_predictions() och visa_spel().
    #
    if not raw_saved_at:
        return ""
    try:
        saved_dt_utc = datetime.fromisoformat(raw_saved_at)
        saved_dt_local = saved_dt_utc.astimezone(ZoneInfo("Europe/Stockholm"))
        return saved_dt_local.strftime("%H:%M")
    except ValueError:
        return ""


#
# SMHI:s standardiserade vadersymbol-koder (1-27), sasom de
# anvands i weather_symbol-faltet. Om nagon enskild kod visar
# fel text jamfort med det faktiska vadret - sag till, sa
# rattar vi just den posten.
#
WEATHER_SYMBOLS = {
    1: "Klart", 2: "Lätt molnighet", 3: "Halvklart", 4: "Molnigt",
    5: "Mycket moln", 6: "Mulet", 7: "Dimma",
    8: "Lätta regnskurar", 9: "Måttliga regnskurar", 10: "Kraftiga regnskurar",
    11: "Åska", 12: "Lätta snöbyar (snöblandat)", 13: "Måttliga snöbyar (snöblandat)",
    14: "Kraftiga snöbyar (snöblandat)", 15: "Lätta snöbyar", 16: "Måttliga snöbyar",
    17: "Kraftiga snöbyar", 18: "Lätt regn", 19: "Måttligt regn", 20: "Kraftigt regn",
    21: "Åska", 22: "Lätt snöblandat regn", 23: "Måttligt snöblandat regn",
    24: "Kraftigt snöblandat regn", 25: "Lätt snöfall", 26: "Måttligt snöfall",
    27: "Kraftigt snöfall",
}


def _format_weather(weather):
    #
    # weather sparas som ett objekt fran den meteorologiska
    # kallan, t.ex.:
    # {"valid_time": "...", "temperature_c": 13.6,
    #  "wind_speed_ms": 1.8, "precipitation_mm": 0.0,
    #  "weather_symbol": 3}
    #
    if not weather:
        return ""
    if isinstance(weather, str):
        return weather
    if not isinstance(weather, dict):
        return str(weather)

    parts = []

    symbol_code = weather.get("weather_symbol")
    if symbol_code is not None:
        parts.append(WEATHER_SYMBOLS.get(symbol_code, f"Symbol {symbol_code}"))

    temp = weather.get("temperature_c")
    if temp is not None:
        parts.append(f"{temp}°C")

    wind = weather.get("wind_speed_ms")
    if wind is not None:
        parts.append(f"{wind} m/s")

    precipitation = weather.get("precipitation_mm")
    if precipitation:
        parts.append(f"{precipitation} mm")

    return ", ".join(parts)


#
# Enkelt delat tillstand for bakgrundspafyllningen av historik-
# databasen. Uppdateras av _run_backfill_in_background(), som kors
# i en separat trad - lases av startsidan for att visa status samt
# av "Uppdatera"-knappens rutt for att undvika dubbelkorningar.
#
_backfill_status = {
    "running": False,
    "last_summary": None,
    "last_error": None,
}
_backfill_lock = threading.Lock()


def _run_backfill_in_background():
    with _backfill_lock:
        if _backfill_status["running"]:
            return
        _backfill_status["running"] = True
        _backfill_status["last_error"] = None

    try:
        summary = run_backfill()
        _backfill_status["last_summary"] = summary
    except Exception as exc:
        _backfill_status["last_error"] = str(exc)
        print(f"[Backfill-bakgrund] Fel: {exc}")
    finally:
        _backfill_status["running"] = False


def _start_backfill_thread():
    thread = threading.Thread(target=_run_backfill_in_background, daemon=True)
    thread.start()


def _maybe_start_automatic_backfill():
    #
    # Kors en gang vid appstart. Startar bara pafyllningen om det
    # gatt tillrackligt lange sedan senaste lyckade genomgangen
    # (se MIN_HOURS_BETWEEN_AUTO_RUNS i backfill_history.py) - sa
    # att tata omstarter av servern inte utloser onodiga ATG-anrop.
    #
    progress = load_progress()
    if should_run_backfill(progress):
        print("[Backfill] Startar automatisk pafyllning i bakgrunden...")
        _start_backfill_thread()
    else:
        print("[Backfill] Hoppar over automatisk pafyllning - kordes nyligen.")


def _detect_xpress(tracks):
    #
    # V86 (och ibland andra flerloppsspel) kors som "Xpress" pa
    # onsdagar - da delas loppen mellan tva banor i samma spel
    # (t.ex. 4 lopp pa Solvalla, 4 pa Åby). Varje lopp har redan
    # sin egen faktiska bana (satt av RaceParser direkt fran
    # ATG:s per-lopp-data), sa Xpress upptacks helt enkelt genom
    # att se om loppen i spelet spanner over mer an en bana.
    #
    unique_tracks = sorted({t for t in tracks if t})
    return {
        "is_xpress": len(unique_tracks) > 1,
        "tracks": unique_tracks,
    }


def _is_fully_evaluated(outcome):
    if outcome is None:
        return False
    return outcome.get("undecided_legs", 0) == 0


def list_predictions():
    if not os.path.isdir(PREDICTIONS_DIR):
        return []

    items = []
    for filename in os.listdir(PREDICTIONS_DIR):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(PREDICTIONS_DIR, filename)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        prediction_id = filename[:-5]
        raw_saved_at = data.get("saved_at", "")
        legs_data = data.get("legs", [])
        is_xpress = _detect_xpress(leg.get("track") for leg in legs_data)["is_xpress"]

        items.append({
            "game_id": prediction_id,
            "spel": data.get("spel", "?"),
            "track": data.get("track", "?"),
            "date": data.get("date", "?"),
            "saved_at": raw_saved_at,
            "saved_time": _format_local_time(raw_saved_at),
            "strategy": data.get("strategy"),
            "risk": data.get("risk"),
            "evaluated": _is_fully_evaluated(data.get("outcome")),
            "is_xpress": is_xpress,
        })

    items.sort(key=lambda item: item["saved_at"], reverse=True)
    return items


def load_prediction(game_id):
    path = os.path.join(PREDICTIONS_DIR, f"{game_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_predictions_by_game(game_id, exclude_prediction_id=None):
    matches = []
    if not os.path.isdir(PREDICTIONS_DIR):
        return matches

    for filename in os.listdir(PREDICTIONS_DIR):
        if not filename.endswith(".json"):
            continue

        prediction_id = filename[:-5]
        if prediction_id == exclude_prediction_id:
            continue

        path = os.path.join(PREDICTIONS_DIR, filename)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        if data.get("game_id") == game_id:
            data["_prediction_id"] = prediction_id
            matches.append(data)

    return matches


def find_strategy_sibling(prediction, prediction_id):
    #
    # Hittar det andra systemet (motsatt garderingsprincip) som
    # genererades for samma ATG-spel, om ett sadant finns. Om
    # flera finns (t.ex. flera jamforelser gjorda over tid) tas
    # den senast sparade.
    #
    game_id = prediction.get("game_id")
    strategy = prediction.get("strategy")

    if not game_id or not strategy:
        return None

    candidates = [
        p for p in find_predictions_by_game(game_id, exclude_prediction_id=prediction_id)
        if p.get("strategy") and p.get("strategy") != strategy
    ]

    if not candidates:
        return None

    candidates.sort(key=lambda p: p.get("saved_at", ""), reverse=True)
    return candidates[0]


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":
        date = request.form["date"]
        return redirect(url_for("banor", date=date))

    predictions = list_predictions()
    open_predictions = [p for p in predictions if not p["evaluated"]]
    archived_predictions = [p for p in predictions if p["evaluated"]]

    progress = load_progress()
    raw_last_backfill = progress.get("last_run_completed_at")
    last_backfill_at = None
    if raw_last_backfill:
        try:
            dt_utc = datetime.fromisoformat(raw_last_backfill)
            dt_local = dt_utc.astimezone(ZoneInfo("Europe/Stockholm"))
            last_backfill_at = dt_local.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            last_backfill_at = None

    return render_page("""
        <form method="post">
            <label>Datum</label>
            <input type="date" name="date" required>
            <button type="submit">Visa banor</button>
        </form>

        <h2>Öppna</h2>
        {% if not open_predictions %}
        <p>Inga öppna spel just nu.</p>
        {% else %}
        <form id="open-pred-form">
            <select id="open-pred-select" name="game_id" style="font-size:0.9rem;">
                {% for p in open_predictions %}
                <option value="{{ p.game_id }}">
                    {{ p.spel }}{% if p.is_xpress %} Xpress{% endif %} - {{ p.track }} - {{ p.date[2:] }}{% if p.saved_time %} ({{ p.saved_time }}){% endif %} [{{ 'G' if p.strategy == 'legacy' else 'N' if p.strategy == 'continuous' else '?' }}] [{{ p.risk[0] if p.risk else '?' }}]
                </option>
                {% endfor %}
            </select>
            <div class="btn-row">
                <button type="button" onclick="goVisa('open-pred-select')">Visa</button>
                <button type="button" onclick="goUtvardera('open-pred-form', 'open-pred-select')">Utvardera</button>
            </div>
        </form>
        {% endif %}

        <h2>Arkiv</h2>
        {% if not archived_predictions %}
        <p>Inga arkiverade spel an.</p>
        {% else %}
        <form id="archive-pred-form">
            <select id="archive-pred-select" name="game_id" style="font-size:0.9rem;">
                {% for p in archived_predictions %}
                <option value="{{ p.game_id }}">
                    {{ p.spel }}{% if p.is_xpress %} Xpress{% endif %} - {{ p.track }} - {{ p.date[2:] }}{% if p.saved_time %} ({{ p.saved_time }}){% endif %} [{{ 'G' if p.strategy == 'legacy' else 'N' if p.strategy == 'continuous' else '?' }}] [{{ p.risk[0] if p.risk else '?' }}]{% if p.evaluated %} - ✓{% endif %}
                </option>
                {% endfor %}
            </select>
            <div class="btn-row">
                <button type="button" onclick="goVisa('archive-pred-select')">Visa</button>
            </div>
        </form>
        {% endif %}

        <script>
            function goVisa(selectId) {
                var select = document.getElementById(selectId);
                window.location.href = '/visa/' + select.value;
            }
            function goUtvardera(formId, selectId) {
                var form = document.getElementById(formId);
                var select = document.getElementById(selectId);
                form.action = '/utvardera/' + select.value;
                form.method = 'post';
                form.submit();
            }
        </script>

        <h2>Historik</h2>
        {% if backfill_running %}
        <p style="color:#8b949e; font-size:0.9rem;">Uppdaterar historikdatabasen i bakgrunden...</p>
        {% elif last_backfill_at %}
        <p style="color:#8b949e; font-size:0.9rem;">Historik senast uppdaterad: {{ last_backfill_at }}</p>
        {% else %}
        <p style="color:#8b949e; font-size:0.9rem;">Historik har inte uppdaterats an.</p>
        {% endif %}
        <form method="post" action="/uppdatera-historik">
            <button type="submit" {% if backfill_running %}disabled{% endif %}>
                {{ "Uppdaterar..." if backfill_running else "Uppdatera historik" }}
            </button>
        </form>

        <a class="footer-link" href="/strategier">Strategijämförelse</a>
    """, open_predictions=open_predictions, archived_predictions=archived_predictions,
        backfill_running=_backfill_status["running"], last_backfill_at=last_backfill_at)


@app.route("/uppdatera-historik", methods=["POST"])
def uppdatera_historik():
    if not _backfill_status["running"]:
        _start_backfill_thread()
    return redirect(url_for("index"))


@app.route("/banor")
def banor():
    date = request.args.get("date")
    calendar = race_collector.get_calendar(date)

    if not calendar.days or not calendar.days[0].track_days:
        return render_page(
            "<p>Inga banor hittades for {{ date }}.</p>"
            "<a class='footer-link' href='/'>Hem</a>",
            date=date,
        )

    track_days = calendar.days[0].track_days

    return render_page("""
        <h1>Banor - {{ date }}</h1>
        {% for t in track_days %}
        <a class="card" href="{{ url_for('spel', date=date, bana=t.name) }}">{{ t.name }}</a>
        {% endfor %}
        <a class="footer-link" href="/">Hem</a>
    """, date=date, track_days=track_days)


@app.route("/spel")
def spel():
    date = request.args.get("date")
    bana = request.args.get("bana")
    calendar = race_collector.get_calendar(date)
    track_day = next(
        (t for t in calendar.days[0].track_days if t.name == bana), None
    )

    if track_day is None:
        return "Banan hittades inte", 404

    games = [
        g for g in track_day.games if g.name.upper() in SYSTEM_BET_TYPES
    ]

    return render_page("""
        <h1>Spel - {{ bana }}</h1>
        {% if not games %}
        <p>Inga flerloppsspel hittades.</p>
        {% endif %}
        {% for g in games %}
        <a class="card" href="{{ url_for('installningar', date=date, bana=bana, game_id=g.id, game_name=g.name) }}">{{ g.name }}</a>
        {% endfor %}
        <a class="footer-link" href="{{ url_for('banor', date=date) }}">Tillbaka</a>
    """, date=date, bana=bana, games=games)


@app.route("/installningar")
def installningar():
    date = request.args.get("date")
    bana = request.args.get("bana")
    game_id = request.args.get("game_id")
    game_name = request.args.get("game_name")

    if game_id != DEMO_GAME_ID and _is_historical_date(date):
        return render_page("""
            <h1>Redan avgjort lopp</h1>
            <p>{{ game_name }} - {{ bana }} - {{ date }} har redan gatt.</p>
            <p>
                Nya system kan bara genereras for kommande eller pagaende lopp,
                eftersom ATG:s odds- och rankingdata for avgjorda lopp kan andras
                i efterhand - vilket gor testresultat missvisande.
            </p>
            <p>
                For att laborera med funktioner, anvand demoloppet istallet:
                <a href="/">ga till startsidan</a> och valj demoloppets datum.
            </p>
            <a class="footer-link" href="/">Hem</a>
        """, game_name=game_name, bana=bana, date=date)

    return render_page("""
        <h1>Installningar</h1>
        <p>{{ game_name }} - {{ bana }}</p>
        <form method="post" action="{{ url_for('resultat') }}">
            <input type="hidden" name="date" value="{{ date }}">
            <input type="hidden" name="bana" value="{{ bana }}">
            <input type="hidden" name="game_id" value="{{ game_id }}">
            <input type="hidden" name="game_name" value="{{ game_name }}">

            <label>Max systemkostnad (kr)</label>
            <input type="number" name="max_cost" value="1000" required>

            <label>Risknivå</label>
            <select name="risk">
                <option>Låg</option>
                <option selected>Mellan</option>
                <option>Hög</option>
            </select>

            <label>Antal spikar</label>
            <input type="number" name="spikes" value="1" min="0" required>

            <label>Antal lås</label>
            <input type="number" name="locks" value="2" min="0" required>

            <label style="display:flex; align-items:center; gap:8px; flex-direction:row;">
                <input type="checkbox" name="compare_strategies" value="1" style="width:auto;">
                Jämför med gamla garderingsprincipen (genererar två system)
            </label>

            <button type="submit">Generera system</button>
        </form>
    """, date=date, bana=bana, game_id=game_id, game_name=game_name)


@app.route("/resultat", methods=["POST"])
def resultat():
    date = request.form["date"]
    bana = request.form["bana"]
    game_id = request.form["game_id"]
    game_name = request.form["game_name"]
    max_cost = int(request.form["max_cost"])
    risk = request.form["risk"]
    spikes = int(request.form["spikes"])
    locks = int(request.form["locks"])
    compare_strategies = request.form.get("compare_strategies") == "1"

    if game_id != DEMO_GAME_ID and _is_historical_date(date):
        return render_page("""
            <h1>Redan avgjort lopp</h1>
            <p>Nya system kan inte genereras for redan avgjorda lopp.</p>
            <a class="footer-link" href="/">Hem</a>
        """)

    game = Game(
        game_id=game_id, name=game_name, track=bana, date=date, races=0
    )

    collector = AnalysisDataCollector()
    analysis_data = collector.collect(game)

    analysis_engine = AnalysisEngine()
    register_modules(analysis_engine)
    analysis_data = analysis_engine.analyze(analysis_data)

    expert_analyzer = ExpertAnalyzer()
    crowd_engine = CrowdEngine()
    chaos_engine = ChaosEngine()
    score_engine = ScoreEngine()

    expert_tips = expert_analyzer.collect_tips(analysis_data.game.id)

    for leg_index, race in enumerate(analysis_data.races, start=1):
        expert_analyzer.apply(race, leg_index, expert_tips)
        crowd_engine.analyze(race)
        chaos_engine.analyze(race)
        score_engine.calculate(race)

    #
    # Analysdatan ovan (kaosvärde, poäng per häst osv) är
    # oberoende av garderingsprincip, så samma analyserade lopp
    # kan återanvändas för att generera flera system parallellt.
    #
    strategies = ["continuous"]
    if compare_strategies:
        strategies.append("legacy")

    system_generator = SystemGenerator()
    prediction_logger = PredictionLogger()
    results = []

    for strategy in strategies:
        leg_selections, total_cost = system_generator.generate(
            races=analysis_data.races,
            max_cost=max_cost,
            risk=risk,
            spikes=spikes,
            locks=locks,
            game_type=analysis_data.game.name,
            coverage_strategy=strategy,
        )

        prediction_logger.save(
            game=analysis_data.game,
            leg_selections=leg_selections,
            total_cost=total_cost,
            selection={
                "max_cost": max_cost, "risk": risk,
                "spikes": spikes, "locks": locks,
            },
            weather=analysis_data.weather,
            strategy=strategy,
        )

        legs_sorted = sorted(
            leg_selections, key=lambda leg: leg["race"].race_number
        )

        results.append({
            "strategy": strategy,
            "legs": legs_sorted,
            "total_cost": total_cost,
        })

    strategy_labels = {
        "continuous": "Ny princip (kontinuerlig gardering)",
        "legacy": "Gammal princip (fast gardering)",
    }

    xpress = _detect_xpress(race.track for race in analysis_data.races)

    return render_page("""
        <h1>Systemförslag</h1>
        <p>
            {{ game_name }}{% if xpress.is_xpress %} Xpress{% endif %} - {{ bana }} - {{ date }}
        </p>
        {% if xpress.is_xpress %}
        <p style="color:#8b949e; font-size:0.9rem;">
            Loppen i detta spel kors pa flera banor: {{ xpress.tracks|join(" + ") }}.
        </p>
        {% endif %}

        {% for result in results %}
        <h2>{{ strategy_labels.get(result.strategy, result.strategy) }}</h2>
        <p>Total kostnad: <b>{{ result.total_cost }} kr</b> (budget {{ max_cost }} kr)</p>

        {% for leg in result.legs %}
        <div class="card leg">
            <b>{{ leg.race }}</b>
            {% if xpress.is_xpress %}<div style="color:#8b949e; font-size:0.85rem;">{{ leg.race.track }}</div>{% endif %}
            <div class="kaos">Kaosvärde: {{ "%.1f"|format(leg.race.kaosvarde or 0) }}</div>
            {% for h in leg.horses %}{{ h.number }}. {{ h.name }}{% if not loop.last %}, {% endif %}{% endfor %}
        </div>
        {% endfor %}
        {% endfor %}

        {% if results|length > 1 %}
        <p>Bada systemen ar sparade separat och kan utvarderas var for sig fran startsidan.</p>
        {% endif %}

        <a class="footer-link" href="/">Hem</a>
    """, results=results, strategy_labels=strategy_labels, game_name=game_name,
        bana=bana, date=date, max_cost=max_cost, xpress=xpress)


@app.route("/visa/<prediction_id>")
def visa_spel(prediction_id):
    prediction = load_prediction(prediction_id)
    if prediction is None:
        return "Spelet hittades inte", 404

    legs = sorted(prediction["legs"], key=lambda leg: leg["race_number"])
    outcome = prediction.get("outcome")

    saved_time = _format_local_time(prediction.get("saved_at", ""))
    weather_display = _format_weather(prediction.get("weather"))
    xpress = _detect_xpress(leg.get("track") for leg in legs)

    leg_reports = {}
    if outcome:
        for r in outcome["legs"]:
            leg_reports[r["race_number"]] = r

    strategy_labels = {
        "continuous": "Ny princip (kontinuerlig gardering)",
        "legacy": "Gammal princip (fast gardering)",
    }

    sibling = find_strategy_sibling(prediction, prediction_id)
    comparison = None
    if sibling and prediction.get("payout") and sibling.get("payout"):
        this_net = prediction["payout"]["net"]
        sibling_net = sibling["payout"]["net"]
        comparison = {
            "this_label": strategy_labels.get(prediction.get("strategy"), prediction.get("strategy")),
            "this_net": this_net,
            "sibling_label": strategy_labels.get(sibling.get("strategy"), sibling.get("strategy")),
            "sibling_net": sibling_net,
            "sibling_id": sibling.get("_prediction_id"),
            "diff": round(this_net - sibling_net, 2),
        }

    return render_page("""
        <img src="{{ url_for('static', filename='brand-light.jpg') }}" alt="" class="print-only brand-seal">

        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
            <h1 style="margin:0;">{{ prediction.spel }}{% if xpress.is_xpress %} Xpress{% endif %}</h1>
            <div class="no-print" style="display:flex; gap:8px;">
                <button type="button" onclick="shareCoupon()"
                    style="width:auto; min-height:auto; padding:8px 14px; font-size:0.85rem;">
                    Dela
                </button>
                <button type="button" onclick="saveAsImage()"
                    style="width:auto; min-height:auto; padding:8px 14px; font-size:0.85rem;">
                    Bild
                </button>
            </div>
        </div>
        <p style="margin-top:0;">
            {% if xpress.is_xpress %}{{ xpress.tracks|join(" + ") }}{% else %}{{ prediction.track }}{% endif %} - {{ prediction.date }}
        </p>

        <p style="display:flex; justify-content:space-between;">
            <span>{{ saved_time }}</span>
            <span>{{ weather_display }}</span>
        </p>

        <p style="font-style:italic; font-size:0.9rem; margin-bottom:2px;">
            Total kostnad: <b>{{ prediction.total_cost }} kr</b> (budget {{ prediction.max_cost }} kr)
        </p>
        <p style="font-style:italic; font-size:0.9rem; margin-top:0;">
            Risk: {{ prediction.risk or '-' }}
        </p>

        {% if prediction.strategy %}
        <p style="color:#8b949e; font-size:0.9rem;">
            {{ strategy_labels.get(prediction.strategy, prediction.strategy) }}
        </p>
        {% endif %}

        {% if sibling and not comparison %}
        <p style="color:#8b949e; font-size:0.85rem;">
            Ett system med {{ strategy_labels.get(sibling.strategy, sibling.strategy) }} finns ocksa sparat for det har loppet,
            men jamforelsen visas forst nar bada ar utvarderade.
        </p>
        {% endif %}

        {% if outcome %}
        <p>
            Traffsakerhet: {{ outcome.hits }}/{{ outcome.evaluated_legs }} avgjorda lopp
            {% if outcome.undecided_legs %}({{ outcome.undecided_legs }} ej avgjorda){% endif %}
        </p>
        {% endif %}
        {% if payout %}
        <div class="card">
            {% if payout.breakdown %}
            {% for entry in payout.breakdown %}
            <p class="hit">{{ entry.level }} rätt: {{ entry.rows }} rad(er) x {{ entry.per_row }} kr = {{ entry.subtotal }} kr</p>
            {% endfor %}
            <p>Total utdelning: <b>{{ payout.total_payout }} kr</b></p>
            {% else %}
            <p>Ingen utdelning denna gång.</p>
            {% endif %}
            <p>Netto (utdelning minus insats): <b>{{ payout.net }} kr</b></p>
        </div>
        {% endif %}

        {% if comparison %}
        <div class="card">
            <b>Jämförelse mot {{ comparison.sibling_label }}</b>
            <p>{{ comparison.this_label }}: <b>{{ comparison.this_net }} kr</b></p>
            <p>{{ comparison.sibling_label }}: <b>{{ comparison.sibling_net }} kr</b></p>
            <p>
                Skillnad:
                <b class="{{ 'hit' if comparison.diff >= 0 else 'miss' }}">
                    {{ '+' if comparison.diff >= 0 else '' }}{{ comparison.diff }} kr
                </b>
                {{ 'till fordel for ' + comparison.this_label if comparison.diff > 0 else 'till fordel for ' + comparison.sibling_label if comparison.diff < 0 else '(lika)' }}
            </p>
            <a href="{{ url_for('visa_spel', prediction_id=comparison.sibling_id) }}">Visa {{ comparison.sibling_label }}</a>
        </div>
        {% endif %}

        {% if history and history|length > 1 %}
        <div class="card">
            <b>Utvärderingshistorik ({{ history|length }} ggr)</b>
            {% for h in history %}
            <p>
                {{ h.evaluated_at[:16].replace('T', ' ') }} -
                {{ h.outcome.hits }}/{{ h.outcome.evaluated_legs }} rätt
                {% if h.payout %}, netto {{ h.payout.net }} kr{% endif %}
            </p>
            {% endfor %}
            <p style="color:#f0883e; font-size:0.85rem;">
                OBS: olika utfall mellan utvärderingar beror pa att ATG:s
                resultatdata for loppet andrats mellan hamtningarna.
            </p>
        </div>
        {% endif %}

        {% if not fully_evaluated %}
        <form class="no-print" method="post" action="{{ url_for('utvardera', prediction_id=prediction_id) }}">
            <button type="submit">Utvardera</button>
        </form>
        {% else %}
        <p class="no-print" style="text-align:center; margin-top:8px;">
            <a href="#" onclick="document.getElementById('force-eval-form').submit(); return false;"
               style="color:#8b949e; font-size:0.85rem;">
                Tvinga omvärdering
            </a>
        </p>
        <form id="force-eval-form" class="no-print" method="post" action="{{ url_for('utvardera', prediction_id=prediction_id) }}" style="display:none;"></form>
        {% endif %}

        {% for leg in legs %}
        <div class="card leg">
            <b>V{{ leg.race_number }}</b>
            {% if xpress.is_xpress %}<div style="color:#8b949e; font-size:0.85rem;">{{ leg.track }}</div>{% endif %}
            <div class="kaos">Kaosvärde: {{ "%.1f"|format(leg.kaosvarde or 0) }}</div>
            {% for h in leg.horses if h.chosen %}{{ h.number }}. {{ h.name }}{% if not loop.last %}, {% endif %}{% endfor %}

            {% set report = leg_reports.get(leg.race_number) %}
            {% if report %}
                {% if report.status == "ej avgjort" %}
                <div class="undecided">Annu ej avgjort</div>
                {% elif report.hit %}
                <div class="hit">TRAFF - vinnare: {{ report.winner_number }}. {{ report.winner_name }}</div>
                {% else %}
                <div class="miss">Miss - vinnare: {{ report.winner_number }}. {{ report.winner_name }}</div>
                {% endif %}
            {% endif %}
        </div>
        {% endfor %}

        <a class="footer-link no-print" href="/">Hem</a>

        <!--
          Dold "exportversion" av kupongen - permanent ljust stylad
          (till skillnad fran resten av sidan, som bara byter till
          ljust lage via @media print). html2canvas kan inte se
          @media print-regler eftersom den bara renderar det som
          redan visas pa skarmen, sa den har versionen finns som
          en separat, alltid-ljus kopia, positionerad utanfor
          skarmen tills "Bild"-knappen trycks.
        -->
        <div id="kupong-export" style="position:absolute; left:-9999px; top:0; width:760px;
             background:#ffffff; color:#000000; padding:32px;
             font-family:-apple-system, Roboto, Helvetica, Arial, sans-serif;">
            <img src="{{ url_for('static', filename='brand-light.jpg') }}" alt=""
                 style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
                        width:70%; max-width:500px; opacity:0.10; z-index:0;">
            <div style="position:relative; z-index:1;">
                <h1 style="color:#000; margin:0 0 2px; font-size:1.8rem;">{{ prediction.spel }}{% if xpress.is_xpress %} Xpress{% endif %}</h1>
                <p style="margin-top:0;">
                    {% if xpress.is_xpress %}{{ xpress.tracks|join(" + ") }}{% else %}{{ prediction.track }}{% endif %} - {{ prediction.date }}
                </p>
                <p style="display:flex; justify-content:space-between;">
                    <span>{{ saved_time }}</span>
                    <span>{{ weather_display }}</span>
                </p>
                <p style="font-style:italic; font-size:0.95rem; margin-bottom:2px;">
                    Total kostnad: <b>{{ prediction.total_cost }} kr</b> (budget {{ prediction.max_cost }} kr)
                </p>
                <p style="font-style:italic; font-size:0.95rem; margin-top:0;">
                    Risk: {{ prediction.risk or '-' }}
                </p>
                {% if prediction.strategy %}
                <p style="color:#444; font-size:0.95rem;">
                    {{ strategy_labels.get(prediction.strategy, prediction.strategy) }}
                </p>
                {% endif %}
                {% if sibling and not comparison %}
                <p style="color:#444; font-size:0.9rem;">
                    Ett system med {{ strategy_labels.get(sibling.strategy, sibling.strategy) }} finns ocksa sparat for det har loppet,
                    men jamforelsen visas forst nar bada ar utvarderade.
                </p>
                {% endif %}
                {% if outcome %}
                <p>
                    Traffsakerhet: {{ outcome.hits }}/{{ outcome.evaluated_legs }} avgjorda lopp
                    {% if outcome.undecided_legs %}({{ outcome.undecided_legs }} ej avgjorda){% endif %}
                </p>
                {% endif %}
                {% if payout %}
                <div style="border:1px solid #000; border-radius:10px; padding:14px; margin-bottom:12px;">
                    {% if payout.breakdown %}
                    {% for entry in payout.breakdown %}
                    <p style="font-weight:bold; margin:4px 0;">{{ entry.level }} rätt: {{ entry.rows }} rad(er) x {{ entry.per_row }} kr = {{ entry.subtotal }} kr</p>
                    {% endfor %}
                    <p>Total utdelning: <b>{{ payout.total_payout }} kr</b></p>
                    {% else %}
                    <p>Ingen utdelning denna gång.</p>
                    {% endif %}
                    <p>Netto (utdelning minus insats): <b>{{ payout.net }} kr</b></p>
                </div>
                {% endif %}
                {% if comparison %}
                <div style="border:1px solid #000; border-radius:10px; padding:14px; margin-bottom:12px;">
                    <b>Jämförelse mot {{ comparison.sibling_label }}</b>
                    <p>{{ comparison.this_label }}: <b>{{ comparison.this_net }} kr</b></p>
                    <p>{{ comparison.sibling_label }}: <b>{{ comparison.sibling_net }} kr</b></p>
                    <p>
                        Skillnad:
                        <b>{{ '+' if comparison.diff >= 0 else '' }}{{ comparison.diff }} kr</b>
                        {{ 'till fordel for ' + comparison.this_label if comparison.diff > 0 else 'till fordel for ' + comparison.sibling_label if comparison.diff < 0 else '(lika)' }}
                    </p>
                </div>
                {% endif %}
                {% for leg in legs %}
                <div style="border:1px solid #000; border-radius:10px; padding:14px; margin-bottom:12px;">
                    <b>V{{ leg.race_number }}</b>
                    {% if xpress.is_xpress %}<div style="color:#444; font-size:0.85rem;">{{ leg.track }}</div>{% endif %}
                    <div style="color:#000; font-size:14px; margin:4px 0;">Kaosvärde: {{ "%.1f"|format(leg.kaosvarde or 0) }}</div>
                    {% for h in leg.horses if h.chosen %}{{ h.number }}. {{ h.name }}{% if not loop.last %}, {% endif %}{% endfor %}
                    {% set report = leg_reports.get(leg.race_number) %}
                    {% if report %}
                        {% if report.status == "ej avgjort" %}
                        <div style="color:#555; margin-top:6px;">Annu ej avgjort</div>
                        {% elif report.hit %}
                        <div style="color:#000; font-weight:bold; margin-top:6px;">TRAFF - vinnare: {{ report.winner_number }}. {{ report.winner_name }}</div>
                        {% else %}
                        <div style="color:#555; margin-top:6px;">Miss - vinnare: {{ report.winner_number }}. {{ report.winner_name }}</div>
                        {% endif %}
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <script>
            function shareCoupon() {
                var shareText = {{ (prediction.spel ~ ' - ' ~ prediction.track ~ ' - ' ~ prediction.date) | tojson }};
                if (navigator.share) {
                    navigator.share({
                        title: shareText,
                        text: shareText,
                        url: window.location.href
                    }).catch(function() {});
                } else {
                    alert('Delning stods inte av den har webblasaren.');
                }
            }

            function saveAsImage() {
                var el = document.getElementById('kupong-export');
                var filename = {{ (prediction.spel ~ '-' ~ prediction.date ~ '.png') | tojson }};

                html2canvas(el, {backgroundColor: '#ffffff', scale: 2}).then(function(canvas) {
                    canvas.toBlob(function(blob) {
                        var file = new File([blob], filename, {type: 'image/png'});

                        if (navigator.canShare && navigator.canShare({files: [file]})) {
                            navigator.share({files: [file], title: filename}).catch(function() {});
                        } else {
                            var url = URL.createObjectURL(blob);
                            var a = document.createElement('a');
                            a.href = url;
                            a.download = filename;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            URL.revokeObjectURL(url);
                        }
                    }, 'image/png');
                }).catch(function() {
                    alert('Kunde inte generera bilden.');
                });
            }
        </script>
    """, prediction=prediction, legs=legs, outcome=outcome, leg_reports=leg_reports,
        fully_evaluated=_is_fully_evaluated(outcome), payout=prediction.get("payout"),
        prediction_id=prediction_id, strategy_labels=strategy_labels,
        saved_time=saved_time, weather_display=weather_display, xpress=xpress,
        sibling=sibling, comparison=comparison, history=prediction.get("evaluation_history"))


@app.route("/utvardera/<prediction_id>", methods=["POST"])
def utvardera(prediction_id):
    learning_engine = LearningEngine()
    learning_engine.evaluate(prediction_id)
    return redirect(url_for("visa_spel", prediction_id=prediction_id))


@app.route("/strategier")
def strategier():
    stats = {}
    by_game = {}

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
            if not _is_fully_evaluated(outcome):
                continue

            strategy = data.get("strategy") or "okand"
            entry = stats.setdefault(strategy, {
                "count": 0,
                "hits": 0,
                "evaluated_legs": 0,
                "total_cost": 0.0,
                "total_payout": 0.0,
                "net": 0.0,
            })

            entry["count"] += 1
            entry["hits"] += outcome.get("hits", 0)
            entry["evaluated_legs"] += outcome.get("evaluated_legs", 0)
            entry["total_cost"] += data.get("total_cost", 0)

            payout = data.get("payout")
            if payout:
                entry["total_payout"] += payout.get("total_payout", 0)
                entry["net"] += payout.get("net", 0)
            else:
                entry["net"] -= data.get("total_cost", 0)

            #
            # Samla ihop per lopp (game_id) for parvis jamforelse,
            # bara for spel som faktiskt har en angiven strategi.
            #
            game_id = data.get("game_id")
            if game_id and data.get("strategy") and payout:
                by_game.setdefault(game_id, []).append({
                    "strategy": data.get("strategy"),
                    "spel": data.get("spel", "?"),
                    "track": data.get("track", "?"),
                    "date": data.get("date", "?"),
                    "net": payout.get("net", 0),
                    "prediction_id": filename[:-5],
                })

    strategy_labels = {
        "continuous": "Ny princip (kontinuerlig gardering)",
        "legacy": "Gammal princip (fast gardering)",
        "okand": "Okänd/äldre spel (fore strategital)",
    }

    rows = []
    for strategy, entry in stats.items():
        hit_rate = (
            round(100 * entry["hits"] / entry["evaluated_legs"], 1)
            if entry["evaluated_legs"] > 0 else None
        )
        rows.append({
            "strategy": strategy,
            "label": strategy_labels.get(strategy, strategy),
            "count": entry["count"],
            "hit_rate": hit_rate,
            "total_cost": round(entry["total_cost"], 2),
            "total_payout": round(entry["total_payout"], 2),
            "net": round(entry["net"], 2),
        })

    rows.sort(key=lambda r: r["net"], reverse=True)

    #
    # Bygg parvisa jamforelser - bara for lopp dar bade continuous
    # och legacy faktiskt har utvarderats.
    #
    pairs = []
    for game_id, entries in by_game.items():
        by_strategy = {e["strategy"]: e for e in entries}
        if "continuous" in by_strategy and "legacy" in by_strategy:
            cont = by_strategy["continuous"]
            leg = by_strategy["legacy"]
            pairs.append({
                "spel": cont["spel"],
                "track": cont["track"],
                "date": cont["date"],
                "continuous_net": round(cont["net"], 2),
                "legacy_net": round(leg["net"], 2),
                "diff": round(cont["net"] - leg["net"], 2),
                "continuous_id": cont["prediction_id"],
                "legacy_id": leg["prediction_id"],
            })

    pairs.sort(key=lambda p: p["date"], reverse=True)

    return render_page("""
        <h1>Strategijämförelse</h1>

        {% if pairs %}
        <h2>Parvis per lopp</h2>
        {% for p in pairs %}
        <div class="card">
            <b>{{ p.spel }} - {{ p.track }} - {{ p.date }}</b>
            <p>Ny princip: <a href="{{ url_for('visa_spel', prediction_id=p.continuous_id) }}">{{ p.continuous_net }} kr</a></p>
            <p>Gammal princip: <a href="{{ url_for('visa_spel', prediction_id=p.legacy_id) }}">{{ p.legacy_net }} kr</a></p>
            <p>
                Skillnad:
                <b class="{{ 'hit' if p.diff >= 0 else 'miss' }}">
                    {{ '+' if p.diff >= 0 else '' }}{{ p.diff }} kr
                </b>
                {{ '(ny princip battre)' if p.diff > 0 else '(gammal princip battre)' if p.diff < 0 else '(lika)' }}
            </p>
        </div>
        {% endfor %}
        {% endif %}

        <h2>Sammanlagt över alla spel</h2>
        {% if not rows %}
        <p>Inga utvärderade spel ännu att jämföra.</p>
        {% else %}
        {% for r in rows %}
        <div class="card">
            <b>{{ r.label }}</b>
            <p>Antal utvärderade spel: {{ r.count }}</p>
            {% if r.hit_rate is not none %}
            <p>Träffsäkerhet: {{ r.hit_rate }} %</p>
            {% endif %}
            <p>Total insats: {{ r.total_cost }} kr</p>
            <p>Total utdelning: {{ r.total_payout }} kr</p>
            <p>Netto: <b class="{{ 'hit' if r.net >= 0 else 'miss' }}">{{ r.net }} kr</b></p>
        </div>
        {% endfor %}
        <p style="color:#8b949e; font-size:0.85rem;">
            Baserat pa alla sparade spel dar samtliga lopp ar avgjorda.
            Fler utvarderade spel ger en mer tillforlitlig jamforelse.
        </p>
        {% endif %}

        <a class="footer-link" href="/">Hem</a>
    """, rows=rows, pairs=pairs)


#
# Startar automatisk pafyllning av historikdatabasen vid uppstart
# (om tillrackligt lange gatt sedan senaste lyckade genomgangen).
# WERKZEUG_RUN_MAIN-kollen forhindrar att detta trigglas dubbelt
# nar Flasks debug-omstartare (reloader) startar processen: env-
# variabeln ar osatt vid det forsta genomlopet (innan reloadern
# startat om processen at sig sjalv), och satt till "true" bara i
# den faktiska arbetsprocessen dar servern verkligen kor - sa
# denna kontroll racker ensam, utan att behova las app.debug (som
# annu inte blivit True vid den har punkten i korningen).
#
if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    _maybe_start_automatic_backfill()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
