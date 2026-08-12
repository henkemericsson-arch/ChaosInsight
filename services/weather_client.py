from datetime import datetime, timezone

from config.track_locations import TRACK_LOCATIONS


class WeatherClient:

    #
    # Hämtar väderprognos från SMHI:s öppna API, SNOW1gv1.
    #
    # OBS: SMHI lade ner det äldre PMP3gv2-API:et 2026-03-31
    # (gav 404) och ersatte det med SNOW1gv1, som har både
    # annan URL och annan datastruktur (platt data-objekt med
    # läsbara parameternamn istället för en lista med korta
    # koder som t/ws/Wsymb2).
    #
    # Dokumentation:
    # https://opendata.smhi.se/metfcst/snow1gv1
    #

    BASE_URL = "https://opendata-download-metfcst.smhi.se/api"

    MISSING_VALUE = 9999

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
            f"{self.BASE_URL}/category/snow1g/version/1/geotype/point/"
            f"lon/{lon}/lat/{lat}/data.json"
        )

        try:
            data = self.http.get(url=url, headers={})
        except Exception as e:
            print(f"[DEBUG] SMHI-anrop misslyckades: {e!r}")
            return None

        return self._parse_forecast(data, when)

    def _parse_forecast(self, data, when):

        time_series = data.get("timeSeries", [])

        if not time_series:
            return None

        target_time = when or datetime.now(timezone.utc)

        closest_entry = min(
            time_series,
            key=lambda entry: abs(
                datetime.fromisoformat(
                    entry["time"].replace("Z", "+00:00")
                )
                - target_time
            ),
        )

        values = closest_entry.get("data", {})

        return {
            "valid_time": closest_entry.get("time"),
            "temperature_c": self._clean(values.get("air_temperature")),
            "wind_speed_ms": self._clean(values.get("wind_speed")),
            "precipitation_mm": self._clean(
                values.get("precipitation_amount_median")
            ),
            "weather_symbol": self._clean(values.get("symbol_code")),
        }

    def _clean(self, value):

        #
        # SMHI använder 9999 som sentinelvärde för
        # "inget värde", inte en riktig mätning.
        #

        if value == self.MISSING_VALUE:
            return None

        return value
