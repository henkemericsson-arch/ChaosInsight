from models.track_day import TrackDay


class RaceDay:

    def __init__(self, date):

        self.date = date

        #
        # Alla banor denna tävlingsdag.
        #

        self.track_days = []

    def get_track(self, track_id):

        for track_day in self.track_days:

            if track_day.id == track_id:
                return track_day

        return None

    def add_track(
        self,
        track_id,
        track_name,
        country,
    ):

        track_day = self.get_track(track_id)

        if track_day is None:

            track_day = TrackDay(
                track_id=track_id,
                track_name=track_name,
                country=country,
            )

            self.track_days.append(track_day)

        return track_day