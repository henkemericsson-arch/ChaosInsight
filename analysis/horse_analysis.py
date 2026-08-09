class HorseAnalysis:

    def analyze(self, horse):

        score = 0

        #
        # Grundpoäng
        #
        score += 50

        #
        # Startspår
        #
        if hasattr(horse, "post_position"):

            pos = horse.post_position

            if pos in [1, 2, 3]:
                score += 8

            elif pos in [4, 5]:
                score += 5

            elif pos in [6, 7]:
                score += 2

            elif pos >= 8:
                score -= 3

        #
        # Odds
        #
        if hasattr(horse, "odds"):

            odds = horse.odds

            if odds is not None:

                if odds < 2:
                    score += 20

                elif odds < 4:
                    score += 15

                elif odds < 8:
                    score += 8

                elif odds < 15:
                    score += 3

        #
        # Driver
        #
        if hasattr(horse, "driver"):

            if horse.driver:
                score += 2

        #
        # Trainer
        #
        if hasattr(horse, "trainer"):

            if horse.trainer:
                score += 2

        horse.score = score

        return horse