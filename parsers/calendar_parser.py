from models.race_calendar import RaceCalendar
from models.race_day import RaceDay
from models.game import Game


class CalendarParser:

    def parse(self, data):

        calendar = RaceCalendar()

        race_day = RaceDay(
            data.get("date")
        )

        tracks = {}

        for track in data.get("tracks", []):
            tracks[track["id"]] = track

        games = data.get("games", {})

        for game_name, game_list in games.items():

            for game in game_list:

                print()
                print("=" * 70)
                print("SPELDATA")
                print("=" * 70)
                print("Speltyp:", game_name)
                print(game)

                track_ids = game.get("tracks", [])

                if not track_ids:
                    continue

                track_id = track_ids[0]

                track = tracks.get(track_id)

                if track is None:
                    continue

                track_day = race_day.add_track(
                    track_id=track["id"],
                    track_name=track["name"],
                    country=track.get("countryCode", "")
                )

                track_day.games.append(
                    Game(
                        game_id=track["id"],
                        name=game_name.upper(),
                        track=track["name"],
                        date=race_day.date,
                        races=len(game.get("races", []))
                    )
                )

        calendar.days.append(race_day)

        return calendar