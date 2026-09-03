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

            #
            # start_position kan saknas (t.ex. struken hast, eller
            # ATG saknar data for just den hasten) - :>2 kraver ett
            # numeriskt varde och kraschar pa None, sa vi bygger
            # utskriftssträngen sarskilt for det faltet istallet
            # for att formatera direkt i f-strangen.
            #
            start_position = horse.get_metric('start_position')
            start_position_display = (
                f"{start_position:>2}" if start_position is not None else " ?"
            )

            print(
                f"{horse.name:20} "
                f"Spår:{start_position_display}  "
                f"Distans:{horse.get_metric('distance')}m  "
                f"Kusk:{horse.get_metric('driver')}"
            )
