import json
import os

from services.atg_client import ATGClient
from parsers.result_parser import ResultParser


class LearningEngine:

    #
    # Jämför ett tidigare sparat systemförslag
    # (från PredictionLogger) mot det faktiska
    # lopputfallet, och rapporterar hur väl systemet
    # träffade rätt. Det här är den andra halvan av
    # lärande-loopen som beskrivs i Chaos Insight Bibeln.
    #
    # Ännu ingen automatisk viktjustering - bara
    # observation och rapportering. Att låta systemet
    # faktiskt lära sig av det här (justera KAMT-vikter
    # över tid) är ett senare steg.
    #

    PREDICTIONS_DIR = "data/races"

    def __init__(self):

        self.client = ATGClient()
        self.result_parser = ResultParser()

    def evaluate(self, game_id):

        path = os.path.join(self.PREDICTIONS_DIR, f"{game_id}.json")

        if not os.path.exists(path):
            print(f"Ingen sparad prognos hittades för {game_id}.")
            return None

        with open(path, encoding="utf-8") as f:
            prediction = json.load(f)

        leg_reports = []

        for leg in prediction["legs"]:

            leg_report = self._evaluate_leg(leg)

            leg_reports.append(leg_report)

        undecided = [r for r in leg_reports if r["status"] == "ej avgjort"]

        decided = [r for r in leg_reports if r["status"] != "ej avgjort"]

        hits = [r for r in decided if r["hit"]]

        outcome = {
            "evaluated_legs": len(decided),
            "hits": len(hits),
            "undecided_legs": len(undecided),
            "legs": leg_reports,
        }

        prediction["outcome"] = outcome

        with open(path, "w", encoding="utf-8") as f:
            json.dump(prediction, f, ensure_ascii=False, indent=2)

        self._print_report(prediction, outcome)

        return outcome

    def _evaluate_leg(self, leg):

        race_id = leg.get("race_id")

        if race_id is None:
            return {
                "race_number": leg["race_number"],
                "status": "ej avgjort",
                "hit": False,
            }

        raw_data = self.client.get_race_result(race_id)

        if raw_data is None:
            return {
                "race_number": leg["race_number"],
                "status": "ej avgjort",
                "hit": False,
            }

        results = self.result_parser.parse(raw_data)

        if results is None:
            return {
                "race_number": leg["race_number"],
                "status": "ej avgjort",
                "hit": False,
            }

        winner = next(
            (r for r in results if r["finish_order"] == 1), None
        )

        chosen_numbers = {h["number"] for h in leg["horses"]}

        hit = winner is not None and winner["number"] in chosen_numbers

        return {
            "race_number": leg["race_number"],
            "status": "avgjort",
            "winner_number": winner["number"] if winner else None,
            "winner_name": winner["name"] if winner else None,
            "chosen_numbers": sorted(chosen_numbers),
            "hit": hit,
        }

    @staticmethod
    def _print_report(prediction, outcome):

        print()
        print("=" * 60)
        print("Learning Engine - utvärdering")
        print("=" * 60)

        spel = prediction["spel"]
        track = prediction["track"]
        date = prediction["date"]

        print(f"Spel: {spel} | Bana: {track} | Datum: {date}")
        print()

        for leg in outcome["legs"]:

            race_number = leg["race_number"]

            if leg["status"] == "ej avgjort":
                print(f"V{race_number}: ej avgjort än")
                continue

            marker = "TRÄFF" if leg["hit"] else "miss "

            winner_number = leg["winner_number"]
            winner_name = leg["winner_name"]
            chosen_numbers = leg["chosen_numbers"]

            print(
                f"V{race_number}: {marker}  "
                f"vinnare: {winner_number}. {winner_name}  "
                f"| dina hästar: {chosen_numbers}"
            )

        print()

        evaluated_legs = outcome["evaluated_legs"]
        hits = outcome["hits"]
        undecided_legs = outcome["undecided_legs"]

        if evaluated_legs > 0:

            hit_rate = round(100 * hits / evaluated_legs, 1)

            print(
                f"Träffsäkerhet: {hits}/{evaluated_legs} "
                f"avgjorda lopp ({hit_rate} %)"
            )

        if undecided_legs > 0:
            print(f"{undecided_legs} lopp är ännu inte avgjorda.")
