class Horse:

    def __init__(
        self,
        number,
        name,
        driver="",
        trainer=""
    ):
        self.number = number
        self.name = name
        self.driver = driver
        self.trainer = trainer

        self.metrics = {}
        self.score = 0.0

    def set_metric(self, key, value):
        self.metrics[key] = value

    def get_metric(self, key):
        return self.metrics.get(key, 0)
