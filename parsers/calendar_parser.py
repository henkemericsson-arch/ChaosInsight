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

        print(
            f"[DEBUG] Banor i rådata: "
            f"{[(t['id'], t['name']) for t in data.get('tracks', [])]}"
        )

        games = data.get("games", {})

        print(f"[DEBUG] Speltyper i rådata: {list(games.keys())}")

        skipped_no_tracks = 0
        skipped_no_match = 0
        matched = 0

        for game_name, game_list in games.items():

            for game in game_list:

                track_ids = game.get("tracks", [])

                if not track_ids:
                    skipped_no_tracks += 1
                    continue

                track_id = track_ids[0]

                track = tracks.get(track_id)

                if track is None:
                    skipped_no_match += 1
                    print(
                        f"[DEBUG] Ingen matchande bana för spel "
                        f"'{game_name}' (id: {game.get('id')}), "
                        f"bana-id i spelet: {track_ids}, "
                        f"kända bana-id: {list(tracks.keys())}"
                    )
                    continue

                matched += 1

                game_id = game.get("id")

                if game_id is None:
                    print(
                        f"[DEBUG] Spel '{game_name}' på "
                        f"{track['name']} saknar id, hoppar över"
                    )
                    continue

                track_day = race_day.add_track(
                    track_id=track["id"],
                    track_name=track["name"],
                    country=track.get("countryCode", "")
                )

                track_day.games.append(
                    Game(
                        game_id=game_id,
                        name=game_name.upper(),
                        track=track["name"],
                        date=race_day.date,
                        races=len(game.get("races", []))
                    )
                )

        print(
            f"[DEBUG] Matchade spel: {matched}, "
            f"utan bana-id: {skipped_no_tracks}, "
            f"utan matchning: {skipped_no_match}"
        )

        calendar.days.append(race_day)

        return calendar