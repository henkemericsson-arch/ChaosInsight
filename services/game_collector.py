from services.atg_client import ATGClient


class GameCollector:

    def __init__(self):
        self.client = ATGClient()

    def collect(self, game):

        return self.client.get_game(game)