"""
Engangsskript for att fylla pa data/history/ med historisk statistik
for 2026, byggt ovanpa den redan befintliga, legitima ATGClient som
resten av ChaosInsight anvander.

Kor fran projektroten:
    python scripts/backfill_history.py

Kan avbrytas nar som helst (t.ex. med CTRL+C) och kors om senare -
redan hamtade game_id hoppas over automatiskt via progressfilen.
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.atg_client import ATGClient
from parsers.race_parser import RaceParser
from parsers.result_parser import ResultParser
from config.bet_types import SYSTEM_BET_TYPES


START_DATE = "2026-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")

OUTPUT_PATH = "data/history/backfill_starts.jsonl"
PROGRESS_PATH = "data/history/backfill_progress.json"

#
# Paus mellan varje anrop till ATG, for att inte belasta deras
# API med en snabb sekvens av tusentals anrop.
#
REQUEST_DELAY_SECONDS = 1.5


def load_progress():
    if not os.path.exists(PROGRESS_PATH):
        return {"processed_game_ids": [], "processed_dates": []}

    with open(PROGRESS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_progress(progress):
    os.makedirs(os.path.dirname(PROGRESS_PATH), exist_ok=True)
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def daterange(start_date_str, end_date_str):
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")

    current = start
    while current <= end:
        yield current.strftime("%Y-%m-%d")
        current += timedelta(days=1)


def collect_game_ids_for_date(client, date_str):
    #
    # Anvander samma kalender-uppslag som webbappen redan gor via
    # RaceCollector, men bara for att lista game_id - vi hamtar
    # sjalva speldatan separat per game_id nedan.
    #
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
    #
    # Ateranvander samma parsers som resten av plattformen for att
    # plocka ut lopp-, hast- och resultatdata - men lagger dessutom
    # till det faktiska resultatet direkt fran samma svar (races[i]
    # innehaller redan "status" och "starts" med resultat inbakat,
    # sa vi slipper ett extra anrop per lopp).
    #
    race_parser = RaceParser()
    result_parser = ResultParser()

    races = race_parser.parse(raw_game_data)
    raw_races_by_number = {
        r.get("number"): r for r in raw_game_data.get("races", [])
    }

    rows = []

    for race in races:
        raw_race = raw_races_by_number.get(race.race_number, {})
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


def main():
    client = ATGClient()
    progress = load_progress()

    processed_game_ids = set(progress["processed_game_ids"])
    processed_dates = set(progress["processed_dates"])

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    total_rows_written = 0
    total_games_processed = 0

    with open(OUTPUT_PATH, "a", encoding="utf-8") as out_file:

        for date_str in daterange(START_DATE, END_DATE):

            if date_str in processed_dates:
                print(f"[Backfill] {date_str} redan klar, hoppar over.")
                continue

            try:
                game_ids = collect_game_ids_for_date(client, date_str)
            except Exception as exc:
                print(f"[Backfill] Kunde inte hamta kalender for {date_str}: {exc}")
                continue

            if not game_ids:
                print(f"[Backfill] {date_str}: inga poolspel hittades.")
                processed_dates.add(date_str)
                progress["processed_dates"] = sorted(processed_dates)
                save_progress(progress)
                continue

            print(f"[Backfill] {date_str}: {len(game_ids)} spel hittade.")

            for game_id in game_ids:
                if game_id in processed_game_ids:
                    continue

                try:
                    raw_game_data = client.get_game(game_id)
                except Exception as exc:
                    print(f"[Backfill] Fel vid hamtning av {game_id}: {exc}")
                    time.sleep(REQUEST_DELAY_SECONDS)
                    continue

                if not raw_game_data:
                    time.sleep(REQUEST_DELAY_SECONDS)
                    continue

                rows = extract_starts(game_id, raw_game_data)

                for row in rows:
                    out_file.write(json.dumps(row, ensure_ascii=False))
                    out_file.write("\n")

                out_file.flush()

                total_rows_written += len(rows)
                total_games_processed += 1

                processed_game_ids.add(game_id)
                progress["processed_game_ids"] = sorted(processed_game_ids)
                save_progress(progress)

                print(
                    f"[Backfill]   {game_id}: {len(rows)} starter sparade "
                    f"(totalt {total_rows_written} rader, "
                    f"{total_games_processed} spel klara)"
                )

                time.sleep(REQUEST_DELAY_SECONDS)

            processed_dates.add(date_str)
            progress["processed_dates"] = sorted(processed_dates)
            save_progress(progress)

    print()
    print("=" * 60)
    print(f"Klart. {total_games_processed} spel, {total_rows_written} rader sparade till {OUTPUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
