class RaceParser:

    def parse(self, game_data):

        #
        # Tar emot rådata för ett helt spel (t.ex. V86)
        # från ATG:s games-endpoint och bygger en lista
        # av Race-objekt, ett per delopp.
        #

        from models.race import Race
        from parsers.horse_parser import HorseParser

        horse_parser = HorseParser()

        races = []

        for race_data in game_data.get("races", []):

            track_data = race_data.get("track") or {}

            horses = [
                horse_parser.parse(start)
                for start in race_data.get("starts", [])
            ]

            race = Race(
                track=track_data.get("name", ""),
                date=race_data.get("date", ""),
                race_number=race_data.get("number"),
                distance=race_data.get("distance"),
                start_method=race_data.get("startMethod", ""),
                horses=horses,
                start_time=race_data.get("startTime"),
                race_id=race_data.get("id"),
            )

            races.append(race)

        return races
