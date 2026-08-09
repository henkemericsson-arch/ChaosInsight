from config.atg import RACINGINFO_BASE_URL, CALENDAR_BASE_URL, HEADERS

from services.http_client import HttpClient

from parsers.calendar_parser import CalendarParser


class ATGClient:

    def __init__(self):

        self.http = HttpClient()

        self.calendar_parser = CalendarParser()

    def get_calendar(self, date):

        url = f"{CALENDAR_BASE_URL}/calendar/day/{date}"

        data = self.http.get(
            url=url,
            headers=HEADERS,
            params={"headToHeadEnabled": "true"},
        )

        return self.calendar_parser.parse(data)

    def get_game(self, game_id):

        url = f"{RACINGINFO_BASE_URL}/games/{game_id}"

        data = self.http.get(
            url=url,
            headers=HEADERS,
        )

        return data
