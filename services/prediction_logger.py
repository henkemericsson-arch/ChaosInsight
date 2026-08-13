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

    def save(self, game, leg_selections, total_cost, selection, weather=None):

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
            "weather": weather,
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

        chosen_numbers = {horse.number for horse in leg["horses"]}

        return {
            "race_id": race.race_id,
            "race_number": race.race_number,
            "track": race.track,
            "distance": race.distance,
            "start_method": race.start_method,
            "kaosvarde": getattr(race, "kaosvarde", None),
            "chosen_numbers": sorted(chosen_numbers),
            "horses": [
                {
                    "number": horse.number,
                    "name": horse.name,
                    "driver": horse.driver,
                    "trainer": horse.trainer,
                    "start_position": horse.start_position,
                    "odds": horse.odds,
                    "bet_percentage": horse.bet_percentage,
                    "shod_front": horse.shod_front,
                    "shod_back": horse.shod_back,
                    "shoe_changed": horse.shoe_changed,
                    "sulky_changed": horse.sulky_changed,
                    "driver_win_pct": horse.driver_win_pct,
                    "trainer_win_pct": horse.trainer_win_pct,
                    "horse_win_pct": horse.horse_win_pct,
                    "total_score": horse.get_metric("total_score"),
                    "crowd_index": horse.get_metric("crowd_index"),
                    "chaos_index": horse.get_metric("chaos_index"),
                    "chosen": horse.number in chosen_numbers,
                }

                #
                # Alla hästar i loppet sparas, inte bara de
                # som valdes till systemet, så att mönster
                # (t.ex. över-/undervärdering) kan läras även
                # för hästar vi inte satsade på.
                #

                for horse in race.horses
            ],
        }
