from models.horse import Horse


#
# ATG:s kanda bantillstand-koder. "light" ar bekraftat fran
# rådata; ovriga (medium/heavy/winter-varianter) ar rimliga
# gissningar baserat pa standard trav-terminologi men INTE
# annu bekraftade mot en riktig ATG-rad med det vardet. Om ett
# okant kod-varde dyker upp visas raw-koden som fallback.
#
TRACK_CONDITION_LABELS = {
    "light": "Lätt bana",
    "mediumheavy": "Något tungt",
    "heavy": "Tung bana",
    "winter": "Vinterbana",
}


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
        race_id: str = None,
        track_condition: str = None,
    ):
        self.track = track
        self.date = date
        self.race_number = race_number
        self.distance = distance
        self.start_method = start_method
        self.horses = horses
        self.start_time = start_time
        self.race_id = race_id

        #
        # Ravardet fran ATG (t.ex. "light"). Anvand
        # track_condition_label for en svensk, lasbar etikett.
        #
        self.track_condition = track_condition

    @property
    def track_condition_label(self):
        if not self.track_condition:
            return None
        return TRACK_CONDITION_LABELS.get(
            self.track_condition, self.track_condition
        )

    def __repr__(self):
        return (
            f"Race("
            f"{self.track}, "
            f"V{self.race_number}, "
            f"{len(self.horses)} hästar)"
        )

