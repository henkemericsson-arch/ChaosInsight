from services.data_loader import DataLoader


class RaceProvider:

    def __init__(self):
        self.loader = DataLoader()

    def load(self, race_file):
        return self.loader.load_race(race_file)
