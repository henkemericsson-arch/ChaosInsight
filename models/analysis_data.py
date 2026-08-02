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

        self.horses = []

        self.drivers = []

        self.trainers = []

        self.statistics = {}

        self.market = {}

        self.forum = {}

        self.experts = {}

        self.history = {}

        self.metadata = {}