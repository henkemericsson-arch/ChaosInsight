from models.race import Race
from models.horse import Horse


class GameParser:
    def parse(self, data):
        races = []

        raw_races = data.get("races", [])

        for index, race_data in enumerate(raw_races, start=1):
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
                #
                # Samma fix som i parsers/race_parser.py: den riktiga
                # V-avdelningen (V1-V8) ar listposition i races-listan,
                # inte ATG:s eget "number"-falt (som bara ar banans
                # egna lokala loppnummer for dagen och kolliderar nar
                # ett spel delas mellan tva banor, t.ex. V86 Xpress).
                #
                race_number=index,
                local_race_number=race_data.get("number"),
                distance=race_data.get("distance"),
                start_method=race_data.get("startMethod"),
                horses=horses,
            )

            races.append(race)

        return races
