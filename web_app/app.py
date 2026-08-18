import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask, request, redirect, url_for, render_template_string

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

app = Flask(__name__)
race_collector = RaceCollector()

PREDICTIONS_DIR = "data/races"

PAGE_HEAD = """<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>Chaos Insight</title>
<style>
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; width: 100%;
    background:#0d1117; color:#e6edf3;
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
    background:#238636; color:white; border:none;
    font-weight:bold; cursor:pointer;
    min-height: 48px;
  }
  button:active { background:#2ea043; }
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
</style>
</head>
<body>
"""

PAGE_FOOT = """
</body>
</html>
"""


def render_page(body_template, **context):
    return render_template_string(PAGE_HEAD + body_template + PAGE_FOOT, **context)


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

        items.append({
            "game_id": data.get("game_id", filename[:-5]),
            "spel": data.get("spel", "?"),
            "track": data.get("track", "?"),
            "date": data.get("date", "?"),
            "saved_at": data.get("saved_at", ""),
            "evaluated": _is_fully_evaluated(data.get("outcome")),
        })

    items.sort(key=lambda item: item["saved_at"], reverse=True)
    return items


def load_prediction(game_id):
    path = os.path.join(PREDICTIONS_DIR, f"{game_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":
        date = request.form["date"]
        return redirect(url_for("banor", date=date))

    predictions = list_predictions()

    return render_page("""
        <h1>Chaos Insight</h1>
        <form method="post">
            <label>Datum</label>
            <input type="date" name="date" required>
            <button type="submit">Visa banor</button>
        </form>

        <h2>Tidigare spel</h2>
        {% if not predictions %}
        <p>Inga sparade spel an.</p>
        {% else %}
        <form id="pred-form">
            <select id="pred-select" name="game_id">
                {% for p in predictions %}
                <option value="{{ p.game_id }}" data-evaluated="{{ '1' if p.evaluated else '0' }}"
                    style="color: {{ '#e6edf3' if p.evaluated else '#3fb950' }};">
                    {{ p.spel }} - {{ p.track }} - {{ p.date }}{{ ' (utvarderat)' if p.evaluated else '' }}
                </option>
                {% endfor %}
            </select>
            <div class="btn-row">
                <button type="button" onclick="goVisa()">Visa</button>
                <button type="button" id="eval-btn" onclick="goUtvardera()">Utvardera</button>
            </div>
        </form>
        <script>
            function selectedGameId() {
                return document.getElementById('pred-select').value;
            }
            function goVisa() {
                window.location.href = '/visa/' + selectedGameId();
            }
            function goUtvardera() {
                var form = document.getElementById('pred-form');
                form.action = '/utvardera/' + selectedGameId();
                form.method = 'post';
                form.submit();
            }
        </script>
        {% endif %}
    """, predictions=predictions)


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

    system_generator = SystemGenerator()
    leg_selections, total_cost = system_generator.generate(
        races=analysis_data.races,
        max_cost=max_cost,
        risk=risk,
        spikes=spikes,
        locks=locks,
        game_type=analysis_data.game.name,
    )

    prediction_logger = PredictionLogger()
    prediction_logger.save(
        game=analysis_data.game,
        leg_selections=leg_selections,
        total_cost=total_cost,
        selection={
            "max_cost": max_cost, "risk": risk,
            "spikes": spikes, "locks": locks,
        },
        weather=analysis_data.weather,
    )

    legs_sorted = sorted(
        leg_selections, key=lambda leg: leg["race"].race_number
    )

    return render_page("""
        <h1>Systemförslag</h1>
        <p>{{ game_name }} - {{ bana }} - {{ date }}</p>
        <p>Total kostnad: <b>{{ total_cost }} kr</b> (budget {{ max_cost }} kr)</p>

        {% for leg in legs %}
        <div class="card leg">
            <b>{{ leg.race }}</b>
            <div class="kaos">Kaosvärde: {{ "%.1f"|format(leg.race.kaosvarde or 0) }}</div>
            {% for h in leg.horses %}{{ h.number }}. {{ h.name }}{% if not loop.last %}, {% endif %}{% endfor %}
        </div>
        {% endfor %}

        <a class="footer-link" href="/">Hem</a>
    """, legs=legs_sorted, game_name=game_name, bana=bana, date=date,
        total_cost=total_cost, max_cost=max_cost)


@app.route("/visa/<game_id>")
def visa_spel(game_id):
    prediction = load_prediction(game_id)
    if prediction is None:
        return "Spelet hittades inte", 404

    legs = sorted(prediction["legs"], key=lambda leg: leg["race_number"])
    outcome = prediction.get("outcome")

    leg_reports = {}
    if outcome:
        for r in outcome["legs"]:
            leg_reports[r["race_number"]] = r

    return render_page("""
        <h1>{{ prediction.spel }}</h1>
        <p>{{ prediction.track }} - {{ prediction.date }}</p>
        <p>Total kostnad: <b>{{ prediction.total_cost }} kr</b> (budget {{ prediction.max_cost }} kr)</p>

        {% if outcome %}
        <p>
            Traffsakerhet: {{ outcome.hits }}/{{ outcome.evaluated_legs }} avgjorda lopp
            {% if outcome.undecided_legs %}({{ outcome.undecided_legs }} ej avgjorda){% endif %}
        </p>
        {% endif %}
        <form method="post" action="{{ url_for('utvardera', game_id=prediction.game_id) }}">
            <button type="submit">{{ 'Utvardera igen' if fully_evaluated else 'Utvardera' }}</button>
        </form>

        {% for leg in legs %}
        <div class="card leg">
            <b>V{{ leg.race_number }}</b>
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

        <a class="footer-link" href="/">Hem</a>
    """, prediction=prediction, legs=legs, outcome=outcome, leg_reports=leg_reports,
        fully_evaluated=_is_fully_evaluated(outcome))


@app.route("/utvardera/<game_id>", methods=["POST"])
def utvardera(game_id):
    learning_engine = LearningEngine()
    learning_engine.evaluate(game_id)
    return redirect(url_for("visa_spel", game_id=game_id))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
