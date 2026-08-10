from models.horse import Horse


class Race:
    def __init__(
        self,
        track: str,
        date: str,
        race_number: int,
        distance: int,
        start_method: str,
        horses: list[Horse],
        start_time: str = None,
    ):
        self.track = track
        self.date = date
        self.race_number = race_number
        self.distance = distance
        self.start_method = start_method
        self.horses = horses
        self.start_time = start_time

    def __repr__(self):
        return (
            f"Race("
            f"{self.track}, "
            f"V{self.race_number}, "
            f"{len(self.horses)} hästar)"
        )
