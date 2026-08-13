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

    def get_race_result(self, race_id):

        #
        # Hämtar utökad loppdata inklusive resultat
        # (finishOrder, place m.m.) för ett avgjort lopp.
        # Samma bas-URL som kalendern (horse-betting-info),
        # inte racinginfo.
        #

        url = f"{CALENDAR_BASE_URL}/races/{race_id}/extended"

        data = self.http.get(
            url=url,
            headers=HEADERS,
        )

        return data
