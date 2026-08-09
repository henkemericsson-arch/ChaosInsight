from models.race import Race
from models.horse import Horse


class GameParser:

    def parse(self, data):

        races = []

        for race_data in data.get("races", []):

            horses = []

            for starter in race_data.get("starts", []):

                horse_data = starter.get("horse", {})

                horse = Horse(
                    id=horse_data.get("id"),
                    name=horse_data.get("name"),
                )

                #
                # Spara hela startinformationen.
                # Analysmotorerna kommer använda detta senare.
                #
                horse.start_number = starter.get("number")
                horse.post_position = starter.get("postPosition")
                horse.driver = starter.get("driver")
                horse.trainer = starter.get("trainer")
                horse.odds = starter.get("odds")

                horses.append(horse)

            race = Race(
                track=data.get("track", ""),
                date=data.get("date", ""),
                race_number=race_data.get("number"),
                distance=race_data.get("distance"),
                start_method=race_data.get("startMethod"),
                horses=horses,
            )

            races.append(race)

        return races