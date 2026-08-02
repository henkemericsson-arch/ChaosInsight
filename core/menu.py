from services.race_collector import RaceCollector


class MainMenu:

    def __init__(self):

        self.collector = RaceCollector()

    def show(self):

        print()
        print("=" * 60)
        print("Chaos Insight")
        print("=" * 60)

        date = input("Datum (YYYY-MM-DD): ")

        calendar = self.collector.get_calendar(date)

        if not calendar.days:

            print("\nIngen tävlingsdag hittades.")
            return None

        race_day = calendar.days[0]

        if not race_day.track_days:

            print("\nInga banor hittades.")
            return None

        #
        # Visa banor
        #

        print("\nTillgängliga banor\n")

        for i, track_day in enumerate(race_day.track_days, start=1):

            print(f"{i}. {track_day.name}")

        print()

        track_choice = int(input("Välj bana: "))

        selected_track = race_day.track_days[track_choice - 1]

        #
        # Visa spel
        #

        print(f"\nSpel på {selected_track.name}\n")

        for i, game in enumerate(selected_track.games, start=1):

            print(f"{i}. {game.name}")

        print()

        game_choice = int(input("Välj spel: "))

        selected_game = selected_track.games[game_choice - 1]

        print()

        max_cost = int(input("Maximal systemkostnad (kr): "))

        print("\nRisknivå\n")
        print("1. Låg")
        print("2. Mellan")
        print("3. Hög")
        print()

        risk_choice = int(input("Välj risknivå: "))

        risk_levels = {
            1: "Låg",
            2: "Mellan",
            3: "Hög",
        }

        print()

        spikes = int(input("Antal spikar: "))

        locks = int(input("Antal lås: "))

        return {

            "calendar": calendar,

            "race_day": race_day,

            "track_day": selected_track,

            "game": selected_game,

            "max_cost": max_cost,

            "risk": risk_levels[risk_choice],

            "spikes": spikes,

            "locks": locks,

        }