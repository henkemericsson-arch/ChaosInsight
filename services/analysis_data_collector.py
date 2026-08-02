from models.analysis_data import AnalysisData


class AnalysisDataCollector:

    def collect(self, game):

        #
        # Skapa analysobjektet
        #

        analysis_data = AnalysisData(game)

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