from rich import print


class HorseAnalysis:

    def analyze(self, horse_name: str):

        print(f"[green]Analyserar häst:[/green] {horse_name}")

        result = {
            "horse": horse_name,
            "speed": 84,
            "form": 91,
            "stamina": 79,
            "risk": 18,
            "score": 88
        }

        print(result)

        return result
