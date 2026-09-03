"""
Skript for att fylla pa den historiska databasen med statistik,
byggt ovanpa den redan befintliga, legitima ATGClient som resten
av ChaosInsight anvander.

Kor fran projektroten (engangs/manuellt):
    python script/backfill_history.py

Kan avbrytas nar som helst (t.ex. med CTRL+C) och kors om senare -
redan hamtade game_id hoppas over automatiskt via progressfilen.

Kärnlogiken (run_backfill) importeras aven av web_app/app.py, som
kor den automatiskt i bakgrunden vid uppstart (om det gatt
tillrackligt lange sedan senaste lyckade korningen) samt via en
"Uppdatera"-knapp i granssnittet.

Skriver via foundation.database_manager.DatabaseManager - kanner
inte langre till databasschemat direkt, enligt Bibelns
grundprincip 3.
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.atg_client import ATGClient
from parsers.race_parser import RaceParser
from parsers.result_parser import ResultParser
from config.bet_types import SYSTEM_BET_TYPES
from foundation.database_manager import DatabaseManager
from services.db import DB_PATH


START_DATE = "2021-10-01"

PROGRESS_PATH = "data/history/backfill_progress.json"

#
# Paus mellan varje anrop till ATG, for att inte belasta deras
# API med en snabb sekvens av tusentals anrop.
#
REQUEST_DELAY_SECONDS = 1.5

#
# Hur lange sedan senaste lyckade automatiska korningen som ska
# ha gatt innan en ny automatisk korning tillats (vid appstart).
# Paverkar INTE den manuella "Uppdatera"-knappen eller CLI-korning,
# som alltid kor direkt oavsett den har grarnsen.
#
MIN_HOURS_BETWEEN_AUTO_RUNS = 12


def load_progress():
    if not os.path.exists(PROGRESS_PATH):
        return {"processed_game_ids": [], "processed_dates": [], "last_run_completed_at": None}

    with open(PROGRESS_PATH, encoding="utf-8") as f:
        progress = json.load(f)

    progress.setdefault("processed_game_ids", [])
    progress.setdefault("processed_dates", [])
    progress.setdefault("last_run_completed_at", None)
    return progress


def save_progress(progress):
    os.makedirs(os.path.dirname(PROGRESS_PATH), exist_ok=True)
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def should_run_backfill(progress, min_hours=MIN_HOURS_BETWEEN_AUTO_RUNS):
    last_run = progress.get("last_run_completed_at")
    if not last_run:
        return True

    try:
        last_run_dt = datetime.fromisoformat(last_run)
    except ValueError:
        return True

    return datetime.now(timezone.utc) - last_run_dt >= timedelta(hours=min_hours)


def daterange(start_date_str, end_date_str):
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")

    current = start
    while current <= end:
        yield current.strftime("%Y-%m-%d")
        current += timedelta(days=1)


def collect_game_ids_for_date(client, date_str):
    calendar = client.get_calendar(date_str)

    game_ids = []

    if not calendar.days or not calendar.days[0].track_days:
        return game_ids

    for track_day in calendar.days[0].track_days:
        for game in track_day.games:
            if game.name.upper() in SYSTEM_BET_TYPES:
                game_ids.append(game.id)

    return game_ids


def extract_starts(game_id, raw_game_data):
    race_parser = RaceParser()
    result_parser = ResultParser()

    races = race_parser.parse(raw_game_data)
    raw_races_by_number = {
        r.get("number"): r for r in raw_game_data.get("races", [])
    }

    rows = []

    for race in races:
        raw_race = raw_races_by_number.get(race.local_race_number, {})
        results = result_parser.parse(raw_race) or []
        results_by_number = {r["number"]: r for r in results}

        for horse in race.horses:
            result = results_by_number.get(horse.number, {})

            rows.append({
                "game_id": game_id,
                "date": race.date,
                "track": race.track,
                "track_condition": race.track_condition,
                "distance": race.distance,
                "start_method": race.start_method,
                "race_number": race.race_number,

                "horse_number": horse.number,
                "horse_name": horse.name,
                "driver": horse.driver,
                "trainer": horse.trainer,
                "start_position": horse.start_position,
                "age": horse.age,
                "sex": horse.sex,
                "odds": horse.odds,
                "bet_percentage": horse.bet_percentage,
                "shod_front": horse.shod_front,
                "shod_back": horse.shod_back,
                "shoe_changed": horse.shoe_changed,
                "sulky_changed": horse.sulky_changed,
                "cart_type": horse.cart_type,
                "career_earnings": horse.career_earnings,
                "driver_win_pct": horse.driver_win_pct,
                "trainer_win_pct": horse.trainer_win_pct,
                "horse_win_pct": horse.horse_win_pct,

                "actual_finish_order": result.get("finish_order"),
                "actual_place": result.get("place"),
                "actual_final_odds": result.get("final_odds"),
                "actual_scratched": result.get("scratched"),
                "actual_galloped": result.get("galloped"),
                "actual_disqualified": result.get("disqualified"),
                "actual_prize_money": result.get("prize_money"),
                "actual_km_time": result.get("km_time"),
                "actual_km_time_status_code": result.get("km_time_status_code"),
            })

    return rows


def run_backfill(end_date=None, log=print):
    end_date = end_date or datetime.now().strftime("%Y-%m-%d")

    client = ATGClient()
    progress = load_progress()

    processed_game_ids = set(progress["processed_game_ids"])
    processed_dates = set(progress["processed_dates"])

    db = DatabaseManager()

    total_rows_written = 0
    total_games_processed = 0

    for date_str in daterange(START_DATE, end_date):

        if date_str in processed_dates:
            continue

        try:
            game_ids = collect_game_ids_for_date(client, date_str)
        except Exception as exc:
            log(f"[Backfill] Kunde inte hamta kalender for {date_str}: {exc}")
            continue

        if not game_ids:
            processed_dates.add(date_str)
            progress["processed_dates"] = sorted(processed_dates)
            save_progress(progress)
            continue

        log(f"[Backfill] {date_str}: {len(game_ids)} spel hittade.")

        for game_id in game_ids:
            if game_id in processed_game_ids:
                continue

            try:
                raw_game_data = client.get_game(game_id)
            except Exception as exc:
                log(f"[Backfill] Fel vid hamtning av {game_id}: {exc}")
                time.sleep(REQUEST_DELAY_SECONDS)
                continue

            if not raw_game_data:
                time.sleep(REQUEST_DELAY_SECONDS)
                continue

            rows = extract_starts(game_id, raw_game_data)

            for row in rows:
                db.insert_backfill_start(row, or_ignore=True)

            db.commit()

            total_rows_written += len(rows)
            total_games_processed += 1

            processed_game_ids.add(game_id)
            progress["processed_game_ids"] = sorted(processed_game_ids)
            save_progress(progress)

            log(
                f"[Backfill]   {game_id}: {len(rows)} starter sparade "
                f"(totalt {total_rows_written} rader, "
                f"{total_games_processed} spel klara)"
            )

            time.sleep(REQUEST_DELAY_SECONDS)

        processed_dates.add(date_str)
        progress["processed_dates"] = sorted(processed_dates)
        save_progress(progress)

    db.close()

    #
    # Bara en fullstandig genomgang utan avbrott raknas som en
    # "lyckad korning" och flyttar fram tidsstampeln som styr nasta
    # automatiska forsok.
    #
    progress["last_run_completed_at"] = datetime.now(timezone.utc).isoformat()
    save_progress(progress)

    summary = {
        "games_processed": total_games_processed,
        "rows_written": total_rows_written,
    }

    log(
        f"[Backfill] Klart. {total_games_processed} spel, "
        f"{total_rows_written} rader sparade till {DB_PATH}"
    )

    return summary


if __name__ == "__main__":
    run_backfill()
