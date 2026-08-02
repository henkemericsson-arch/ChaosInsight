class Game:

    def __init__(
        self,
        game_id,
        name,
        track,
        date,
        races,
    ):

        self.id = game_id
        self.name = name
        self.track = track
        self.date = date
        self.races = races

    def __str__(self):

        return (
            f"{self.name} | "
            f"{self.track} | "
            f"{self.date} | "
            f"{self.races} lopp"
        )