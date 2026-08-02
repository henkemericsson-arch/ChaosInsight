from services.knowledge_base import KnowledgeBase


class ScoreEngine:

    def __init__(self):
        self.knowledge = KnowledgeBase()

    def calculate(self, race):

        for horse in race.horses:

            info = self.knowledge.load("horses", horse.name)

            if info:

                win_percent = info.get("win_percent", 0)

                score = (
                    horse.get_metric("speed") * 0.30 +
                    horse.get_metric("form") * 0.25 +
                    horse.get_metric("stamina") * 0.20 +
                    win_percent * 0.25 -
                    horse.get_metric("risk") * 0.10
                )

            else:

                score = (
                    horse.get_metric("speed") * 0.35 +
                    horse.get_metric("form") * 0.30 +
                    horse.get_metric("stamina") * 0.20 -
                    horse.get_metric("risk") * 0.15
                )

            horse.set_metric("score", round(score, 2))
