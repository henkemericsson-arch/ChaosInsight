from analysis.modules.base_analyzer import BaseAnalyzer


class BasicMetricsAnalyzer(BaseAnalyzer):

    name = "Grunddata"

    def analyze(self, race):

        print()
        print("=== Grunddata ===")

        for horse in race.horses:

            horse.set_metric(
                "start_position",
                horse.start_position
            )

            horse.set_metric(
                "distance",
                race.distance
            )

            horse.set_metric(
                "track",
                race.track
            )

            horse.set_metric(
                "driver",
                horse.driver
            )

            horse.set_metric(
                "trainer",
                horse.trainer
            )

            print(
                f"{horse.name:20} "
                f"Spår:{horse.get_metric('start_position'):>2}  "
                f"Distans:{horse.get_metric('distance')}m  "
                f"Kusk:{horse.get_metric('driver')}"
            )