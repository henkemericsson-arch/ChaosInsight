class Game:

    def __init__(
        self,
        game_id,
        name,
        track,
        date,
        races,
        race_ids=None,
        start_time=None,
    ):

        self.id = game_id
        self.name = name
        self.track = track
        self.date = date
        self.races = races

        self.race_ids = race_ids or []
        self.start_time = start_time

    def __str__(self):

        return (
            f"{self.name} | "
            f"{self.track} | "
            f"{self.date} | "
            f"{self.races} lopp"
        )