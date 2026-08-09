from models.analysis_data import AnalysisData

from services.atg_client import ATGClient
from parsers.race_parser import RaceParser


class AnalysisDataCollector:

    def __init__(self):

        self.client = ATGClient()

        self.race_parser = RaceParser()

    def collect(self, game):

        #
        # Skapa analysobjektet
        #

        analysis_data = AnalysisData(game)

        #
        # Hämta rådata för det valda spelet (t.ex. V86)
        # och bygg riktiga Race-objekt med hästar.
        #

        raw_game_data = self.client.get_game(game.id)

        races = self.race_parser.parse(raw_game_data)

        analysis_data.races = races

        #
        # Tills analysmotorn kan hantera flera lopp
        # samtidigt (ett per delopp i systemet), fylls
        # de "platta" fälten med det första loppet så
        # att befintliga analysmoduler fungerar.
        #

        if races:

            first_race = races[0]

            analysis_data.horses = first_race.horses
            analysis_data.track = first_race.track
            analysis_data.distance = first_race.distance

        #
        # Här kommer framtida datainsamling ske.
        #
        # Exempel:
        #
        # analysis_data.weather
        # analysis_data.market
        # analysis_data.statistics
        # analysis_data.history
        # analysis_data.forum
        #

        return analysis_data