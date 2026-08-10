from datetime import datetime, timezone

from config.track_locations import TRACK_LOCATIONS


class WeatherClient:

    #
    # Hämtar väderprognos från SMHI:s öppna API
    # (öppen data, ingen nyckel krävs).
    #
    # Dokumentation:
    # https://opendata.smhi.se/apidocs/metfcst/
    #

    BASE_URL = "https://opendata-download-metfcst.smhi.se/api"

    def __init__(self):

        from services.http_client import HttpClient

        self.http = HttpClient()

    def get_weather(self, track_name, when=None):

        #
        # Returnerar väderdata för banan vid tidpunkten
        # "when" (datetime, UTC). Om ingen tidpunkt anges
        # används närmaste tillgängliga prognos.
        #
        # Returnerar None om banan saknar kända koordinater
        # (t.ex. utländska banor som SMHI inte täcker).
        #

        coordinates = TRACK_LOCATIONS.get(track_name)

        if coordinates is None:
            return None

        lat, lon = coordinates

        url = (
            f"{self.BASE_URL}/category/pmp3g/version/2/geotype/point/"
            f"lon/{lon}/lat/{lat}/data.json"
        )

        try:
            data = self.http.get(url=url, headers={})
        except Exception:
            return None

        return self._parse_forecast(data, when)

    @staticmethod
    def _parse_forecast(data, when):

        time_series = data.get("timeSeries", [])

        if not time_series:
            return None

        target_time = when or datetime.now(timezone.utc)

        closest_entry = min(
            time_series,
            key=lambda entry: abs(
                datetime.fromisoformat(
                    entry["validTime"].replace("Z", "+00:00")
                )
                - target_time
            ),
        )

        parameters = {
            p["name"]: p["values"][0]
            for p in closest_entry.get("parameters", [])
            if p.get("values")
        }

        return {
            "valid_time": closest_entry.get("validTime"),
            "temperature_c": parameters.get("t"),
            "wind_speed_ms": parameters.get("ws"),
            "precipitation_mm": parameters.get("pmedian"),
            "weather_symbol": parameters.get("Wsymb2"),
        }
