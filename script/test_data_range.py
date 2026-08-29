"""
Testar hur langt tillbaka ATG:s racinginfo-API faktiskt har data,
genom att prova kalenderanrop for ett antal datum langre och langre
tillbaka i tiden.

Kor fran projektroten:
    python script/test_data_range.py
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.atg_client import ATGClient
from config.bet_types import SYSTEM_BET_TYPES


def has_games(client, date_str):
    try:
        calendar = client.get_calendar(date_str)
    except Exception as exc:
        return None, str(exc)

    if not calendar.days or not calendar.days[0].track_days:
        return False, None

    for track_day in calendar.days[0].track_days:
        for game in track_day.games:
            if game.name.upper() in SYSTEM_BET_TYPES:
                return True, None

    return False, None


def main():
    client = ATGClient()
    today = datetime.now()

    #
    # Testa ett datum per halvar, upp till 5 ar tillbaka.
    #
    test_points_months_back = [0, 6, 12, 18, 24, 36, 48, 60]

    print("Testar hur langt tillbaka ATG:s racinginfo-API har data:")
    print()

    for months_back in test_points_months_back:
        test_date = today - timedelta(days=months_back * 30)
        date_str = test_date.strftime("%Y-%m-%d")

        found, error = has_games(client, date_str)

        if error:
            print(f"  {date_str} ({months_back} man tillbaka): FEL - {error}")
        elif found:
            print(f"  {date_str} ({months_back} man tillbaka): OK - poolspel hittades")
        else:
            print(f"  {date_str} ({months_back} man tillbaka): inga poolspel den dagen (kan vara en vilodag, inte nodvandigtvis API-granesen)")


if __name__ == "__main__":
    main()
