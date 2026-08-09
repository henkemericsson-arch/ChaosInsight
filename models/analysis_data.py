class AnalysisData:

    def __init__(self, game):

        #
        # Grundinformation
        #

        self.game = game

        #
        # Data som senare fylls av
        # AnalysisDataCollector
        #

        self.weather = None

        self.track = None

        self.distance = None

        #
        # De faktiska loppen i spelet, med hästar,
        # fyllda av AnalysisDataCollector via RaceParser.
        #

        self.races = []

        self.horses = []

        self.drivers = []

        self.trainers = []

        self.statistics = {}

        self.market = {}

        self.forum = {}

        self.experts = {}

        self.history = {}

        self.metadata = {}