from services.atg_client import ATGClient


class RaceCollector:

    def __init__(self):

        self.client = ATGClient()

    def get_calendar(self, date):

        return self.client.get_calendar(date)