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
    ):
        self.track = track
        self.date = date
        self.race_number = race_number
        self.distance = distance
        self.start_method = start_method
        self.horses = horses

    def __repr__(self):
        return (
            f"Race("
            f"{self.track}, "
            f"V{self.race_number}, "
            f"{len(self.horses)} hästar)"
        )
