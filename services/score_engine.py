from learning.trav.parameters import get_provider as get_parameter_provider


class ScoreEngine:

    #
    # Kombinerar CrowdIndex och KaosIndex till ett Total
    # Score per häst, enligt KAMT-modellens grundformel:
    #
    #   Total Score = 0,50 x CrowdIndex + 0,50 x KaosIndex
    #
    # ScoreEngine gör ingen egen analys, den bara väger
    # samman metrics som redan satts av CrowdEngine och
    # ChaosEngine.
    #

    #
    # Vikterna kommer från ParameterProvider (score.crowd, score.chaos);
    # baseline 0,50 / 0,50 ligger i learning/trav/parameter_schema.py.
    #

    def __init__(self, parameters=None):
        self.parameters = parameters or get_parameter_provider()

    def calculate(self, race):

        weights = self.parameters.group("score")

        for horse in race.horses:

            crowd_index = horse.get_metric("crowd_index")
            chaos_index = horse.get_metric("chaos_index")

            total_score = (
                (crowd_index * weights["crowd"])
                + (chaos_index * weights["chaos"])
            )

            horse.set_metric("total_score", round(total_score, 1))

        self._print_ranking(race)

    @staticmethod
    def _print_ranking(race):

        ranked_horses = sorted(
            race.horses,
            key=lambda h: h.get_metric("total_score"),
            reverse=True,
        )

        print()
        print("=== Total Score (rankning) ===")

        for placement, horse in enumerate(ranked_horses, start=1):

            print(
                f"{placement:>2}. {horse.number:>2}. {horse.name:<20} "
                f"CI: {horse.get_metric('crowd_index'):<6} "
                f"KI: {horse.get_metric('chaos_index'):<6} "
                f"Total Score: {horse.get_metric('total_score')}"
            )
