from config.atg import BASE_URL, HEADERS

from services.http_client import HttpClient

from parsers.calendar_parser import CalendarParser


class ATGClient:

    def __init__(self):

        self.http = HttpClient()

        self.calendar_parser = CalendarParser()

    def get_calendar(self, date):

        url = f"{BASE_URL}/calendar/day/{date}"

        data = self.http.get(
            url=url,
            headers=HEADERS,
        )

        return self.calendar_parser.parse(data)

    def get_game(self, game):

        url = f"{BASE_URL}/..."

        data = self.http.get(
            url=url,
            headers=HEADERS,
        )

        return datame