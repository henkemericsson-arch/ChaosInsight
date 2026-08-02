from services.knowledge_base import KnowledgeBase


class ScoreEngine:

    def __init__(self):
        self.knowledge = KnowledgeBase()

    def calculate(self, race):

        for horse in race.horses:

            info = self.knowledge.load("horses", horse.name)

            speed = horse.get_metric("speed")
            form = horse.get_metric("form")
            stamina = horse.get_metric("stamina")
            risk = horse.get_metric("risk")
            driver = horse.get_metric("driver_score")
            trainer = horse.get_metric("trainer_score")
            horse_score = horse.get_metric("horse_score")

            if info:

                win_percent = info.get("win_percent", 0)

                score = (
                    speed * 0.20 +
                    form * 0.15 +
                    stamina * 0.15 +
                    driver * 0.15 +
                    trainer * 0.10 +
                    horse_score * 0.15 +
                    win_percent * 0.20 -
                    risk * 0.10
                )

            else:

                score = (
                    speed * 0.25 +
                    form * 0.20 +
                    stamina * 0.20 +
                    driver * 0.20 +
                    trainer * 0.15 -
                    risk * 0.10
                )

            horse.set_metric("score", round(score, 2))