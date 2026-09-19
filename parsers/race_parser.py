class RaceParser:
    #
    # Tar emot rådata för ett helt spel (t.ex. V86) från ATG:s
    # games-endpoint och bygger en lista av Race-objekt, ett
    # per delopp.
    #
    def parse(self, game_data):
        from models.race import Race
        from parsers.horse_parser import HorseParser

        horse_parser = HorseParser()
        races = []

        raw_races = game_data.get("races", [])

        for index, race_data in enumerate(raw_races, start=1):
            track_data = race_data.get("track") or {}

            #
            # Strukna hästar (redan strukna vid genereringstillfället)
            # ska aldrig bli ett val i ett nytt system - de kan
            # rimligen inte vinna. Filtreras bort redan här, sa att
            # ingen konsument (SystemGenerator, RaceAnalyzer,
            # ChaosEngine, CrowdEngine, kaosvärdesberäkning) behöver
            # hantera det separat, och fältstorleken (t.ex. "12
            # hästar") speglar korrekt hur många som faktiskt kan
            # vinna.
            #
            # OBS: detta är skilt från reservsubstitutionen i
            # Learning Engine, som hanterar det MOTSATTA fallet - en
            # häst som blir struken EFTER att ett system redan
            # sparats. Den logiken rör aldrig denna filtrering, och
            # denna filtrering rör aldrig den.
            #
            horses = [
                horse_parser.parse(start)
                for start in race_data.get("starts", [])
                if not start.get("scratched")
            ]

            race = Race(
                track=track_data.get("name", ""),
                date=race_data.get("date", ""),
                #
                # OBS: race_number ar INTE ATG:s eget "number"-falt
                # langre. Det faltet ar bara respektive banas egna
                # lokala loppnummer for dagen, vilket kolliderar nar
                # ett spel delas mellan tva banor (t.ex. V86 Xpress
                # pa onsdagar - Solvalla och Åby kan bada ha ett
                # "lopp 7" samma kvall). Den riktiga V-avdelningen
                # (V1-V8) ar istallet listposition i races-listan,
                # som alltid ar i kronologisk startordning oavsett
                # bana.
                #
                race_number=index,
                #
                # ATG:s ursprungliga lokala loppnummer sparas kvar
                # separat (anvands inte som nyckel nagonstans) - kan
                # vara anvandbart for felsokning eller framtida
                # visning ("lopp 7 pa Åby").
                #
                local_race_number=race_data.get("number"),
                distance=race_data.get("distance"),
                start_method=race_data.get("startMethod", ""),
                horses=horses,
                start_time=race_data.get("startTime"),
                race_id=race_data.get("id"),
                track_condition=track_data.get("condition"),
            )

            races.append(race)

        return races
