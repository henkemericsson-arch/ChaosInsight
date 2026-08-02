class TrackDay:

    def __init__(
        self,
        track_id,
        track_name,
        country,
    ):

        self.id = track_id

        self.name = track_name

        self.country = country

        #
        # Vilka spel som finns på banan.
        #

        self.games = []

        #
        # Startlistor.
        # Fylls i senare.
        #

        self.races = []