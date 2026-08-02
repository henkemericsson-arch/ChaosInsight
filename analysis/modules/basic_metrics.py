import random


class BasicMetricsAnalyzer:

    def analyze(self, race):

        print()
        print("=== Grundanalys ===")

        for horse in race.horses:

            horse.set_metric("speed", random.randint(70, 100))
            horse.set_metric("form", random.randint(70, 100))
            horse.set_metric("stamina", random.randint(70, 100))
            horse.set_metric("risk", random.randint(0, 30))

            print(
                f"{horse.number:2}. "
                f"{horse.name:20}"
                f" Speed:{horse.get_metric('speed'):3}"
                f" Form:{horse.get_metric('form'):3}"
                f" Stamina:{horse.get_metric('stamina'):3}"
                f" Risk:{horse.get_metric('risk'):3}"
            )
