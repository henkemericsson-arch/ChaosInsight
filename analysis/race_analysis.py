from analysis.horse_analysis import HorseAnalysis


class RaceAnalysis:

    def __init__(self):

        self.horse_analysis = HorseAnalysis()

    def analyze(self, race):

        analyzed = []

        for horse in race.horses:

            analyzed.append(
                self.horse_analysis.analyze(horse)
            )

        analyzed.sort(
            key=lambda h: h.score,
            reverse=True,
        )

        return analyzedltce)