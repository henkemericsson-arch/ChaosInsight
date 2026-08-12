import json
import os
from datetime import datetime, timezone


class PredictionLogger:

    #
    # Sparar systemets föreslagna spelsystem till en JSON-fil,
    # så att Learning Engine senare kan jämföra förslaget mot
    # det faktiska lopputfallet.
    #
    # Detta är den första halvan av lärande-loopen (Bibelns
    # Learning Engine): "vad föreslog systemet". Den andra
    # halvan, "vad blev utfallet", kräver en ny ATG-endpoint
    # för avgjorda lopp som vi ännu inte har sett strukturen
    # på.
    #

    OUTPUT_DIR = "data/races"

    def save(self, game, leg_selections, total_cost, selection):

        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

        record = {
            "game_id": game.id,
            "track": game.track,
            "date": game.date,
            "spel": game.name,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "max_cost": selection["max_cost"],
            "risk": selection["risk"],
            "spikes": selection["spikes"],
            "locks": selection["locks"],
            "total_cost": total_cost,
            "legs": [
                self._leg_to_dict(leg)
                for leg in leg_selections
            ],

            #
            # Fylls i senare av Learning Engine när det
            # faktiska utfallet är känt.
            #

            "outcome": None,
        }

        path = os.path.join(self.OUTPUT_DIR, f"{game.id}.json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        print(f"\n[Prediction Logger] Sparade förslaget till {path}")

    @staticmethod
    def _leg_to_dict(leg):

        race = leg["race"]

        return {
            "race_number": race.race_number,
            "track": race.track,
            "kaosvarde": getattr(race, "kaosvarde", None),
            "horses": [
                {
                    "number": horse.number,
                    "name": horse.name,
                    "total_score": horse.get_metric("total_score"),
                    "crowd_index": horse.get_metric("crowd_index"),
                    "chaos_index": horse.get_metric("chaos_index"),
                }
                for horse in leg["horses"]
            ],
        }
