from analysis.modules.base_analyzer import BaseAnalyzer


class StartlistAnalyzer(BaseAnalyzer):

    name = "Startlista"

    def analyze(self, race):

        print()
        print("=== Startlista ===")

        for horse in race.horses:
            print(f"{horse.number:2}. {horse.name}")
