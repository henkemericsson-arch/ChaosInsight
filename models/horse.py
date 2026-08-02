class Horse:

    def __init__(
        self,
        number,
        name,
        driver="",
        trainer="",
        start_position=None,
        odds=None,
        age=None,
        sex=None,
    ):

        self.number = number
        self.name = name

        self.driver = driver
        self.trainer = trainer

        self.start_position = start_position
        self.odds = odds
        self.age = age
        self.sex = sex

        self.metrics = {}
        self.score = 0.0

    def set_metric(self, key, value):
        self.metrics[key] = value

    def get_metric(self, key):
        return self.metrics.get(key, 0)

    def __repr__(self):
        return f"<Horse {self.number} {self.name}>"
