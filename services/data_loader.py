import json
from pathlib import Path

from models.horse import Horse
from models.race import Race


class DataLoader:

    def __init__(self):
        self.base_path = Path("data")

    def load_race(self, relative_path: str):

        file_path = self.base_path / relative_path

        if not file_path.exists():
            raise FileNotFoundError(f"Hittar inte {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        horses = []

        for horse in data["horses"]:
            horses.append(
                Horse(
                    number=horse["number"],
                    name=horse["name"],
                    driver=horse.get("driver", ""),
                    trainer=horse.get("trainer", ""),
                    start_position=horse.get(
                        "start_position",
                        horse.get("number")
                    ),
                    odds=horse.get("odds"),
                    age=horse.get("age"),
                    sex=horse.get("sex"),
                )
            )

        race = data["race"]

        return Race(
            track=race["track"],
            date=race["date"],
            race_number=race["race_number"],
            distance=race["distance"],
            start_method=race["start_method"],
            horses=horses,
        )
