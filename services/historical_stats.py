import json
import os
from collections import defaultdict


class HistoricalStatsProvider:
    #
    # Laddar in den insamlade historiska starttabellen (fran
    # backfill/observations) en gang, och exponerar harledda
    # per-hast-statistik som ChaosEngine anvander for att fylla
    # i KAMT-modellens historik-beroende komponenter
    # (distansstatistik, bana/underlag, galopprisk, tempoanalys).
    #
    # Alla metoder returnerar None om det inte finns tillrackligt
    # med historik for att saga nagot meningsfullt - anroparen
    # ansvarar for att falla tillbaka pa ett neutralt varde da
    # (se ChaosEngine).
    #

    DEFAULT_PATHS = [
        "data/history/backfill_starts.jsonl",
        "data/history/observations.jsonl",
    ]

    def __init__(self, paths=None):
        self._starts_by_horse = defaultdict(list)
        #
        # (game_id, race_number) -> lista av rader, for att kunna
        # rakna ut faltets snitt-km-tid per historiskt lopp
        # (anvands av tempo_differential).
        #
        self._races = defaultdict(list)

        self._load(paths or self.DEFAULT_PATHS)

    def _load(self, paths):
        for path in paths:
            if not os.path.exists(path):
                continue

            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    horse_name = row.get("horse_name")
                    if not horse_name:
                        continue

                    self._starts_by_horse[horse_name].append(row)

                    game_id = row.get("game_id")
                    race_number = row.get("race_number")
                    if game_id is not None and race_number is not None:
                        self._races[(game_id, race_number)].append(row)

    @staticmethod
    def _parse_km_time_seconds(km_time_str):
        #
        # Format "M.SS,T" (t.ex. "1.14,0") -> totalt antal
        # sekunder som flyttal.
        #
        if not km_time_str:
            return None

        try:
            minutes_part, rest = km_time_str.split(".")
            seconds_part, tenths_part = rest.split(",")

            minutes = int(minutes_part)
            seconds = int(seconds_part)
            tenths = int(tenths_part)

            return minutes * 60 + seconds + tenths / 10
        except (ValueError, AttributeError):
            return None

    def distance_score(self, horse_name, target_distance, margin=100):
        #
        # Vinstprocent (0-100) bland hastens historiska starter
        # inom distansmarginalen. None om ingen matchande start
        # finns.
        #
        if target_distance is None:
            return None

        starts = self._starts_by_horse.get(horse_name, [])

        matching = [
            s for s in starts
            if s.get("distance") is not None
            and abs(s["distance"] - target_distance) <= margin
            and not s.get("actual_scratched")
        ]

        if not matching:
            return None

        wins = sum(1 for s in matching if s.get("actual_finish_order") == 1)
        return round(100 * wins / len(matching), 1)

    def track_condition_score(self, horse_name, target_condition):
        #
        # Vinstprocent (0-100) bland hastens historiska starter
        # pa exakt samma bantyp. None om ingen matchande start
        # finns.
        #
        if not target_condition:
            return None

        starts = self._starts_by_horse.get(horse_name, [])

        matching = [
            s for s in starts
            if s.get("track_condition") == target_condition
            and not s.get("actual_scratched")
        ]

        if not matching:
            return None

        wins = sum(1 for s in matching if s.get("actual_finish_order") == 1)
        return round(100 * wins / len(matching), 1)

    def gallop_risk_score(self, horse_name):
        #
        # 100 x (1 - galoppfrekvens) - fler galopper ger lagre
        # poang. None om hasten saknar historiska starter helt.
        #
        starts = [
            s for s in self._starts_by_horse.get(horse_name, [])
            if not s.get("actual_scratched")
        ]

        if not starts:
            return None

        gallops = sum(1 for s in starts if s.get("actual_galloped"))
        gallop_rate = gallops / len(starts)

        return round(100 * (1 - gallop_rate), 1)

    def tempo_differential(self, horse_name, target_distance, margin=100):
        #
        # Hastens genomsnittliga km-tid (sekunder) relativt
        # faltets snitt i samma historiska lopp, over starter
        # inom distansmarginalen. Negativt varde = hasten var i
        # snitt snabbare an faltet. None om otillracklig data.
        #
        # OBS: detta ar en tidsdifferens i sekunder, inte redan
        # en 0-100-skala - ChaosEngine min-max-normaliserar
        # detta varde inom det aktuella loppets falt innan det
        # anvands.
        #
        if target_distance is None:
            return None

        starts = self._starts_by_horse.get(horse_name, [])
        diffs = []

        for s in starts:
            if (
                s.get("actual_scratched")
                or s.get("actual_galloped")
                or s.get("actual_disqualified")
            ):
                continue

            if s.get("distance") is None or abs(s["distance"] - target_distance) > margin:
                continue

            horse_seconds = self._parse_km_time_seconds(s.get("actual_km_time"))
            if horse_seconds is None:
                continue

            race_key = (s.get("game_id"), s.get("race_number"))
            race_rows = self._races.get(race_key, [])

            field_times = [
                self._parse_km_time_seconds(r.get("actual_km_time"))
                for r in race_rows
                if r.get("actual_km_time") and not r.get("actual_scratched")
            ]
            field_times = [t for t in field_times if t is not None]

            if len(field_times) < 2:
                #
                # Inte tillrackligt med faltdata i just det
                # historiska loppet for att rakna ett meningsfullt
                # snitt.
                #
                continue

            field_avg = sum(field_times) / len(field_times)
            diffs.append(horse_seconds - field_avg)

        if not diffs:
            return None

        return round(sum(diffs) / len(diffs), 3)


#
# Enkel processminnescache sa att den ofta ganska stora
# historikfilen inte laddas om fran disk vid varje loppanalys.
#
_default_provider = None


def get_default_provider():
    global _default_provider
    if _default_provider is None:
        _default_provider = HistoricalStatsProvider()
    return _default_provider
