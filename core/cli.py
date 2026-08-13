import typer

from core.controller import Controller
from services.learning_engine import LearningEngine

app = typer.Typer()


@app.command()
def start():

    controller = Controller()
    controller.run()


@app.command()
def evaluate(game_id: str):

    #
    # Jämför ett tidigare sparat systemförslag mot det
    # faktiska lopputfallet. game_id är samma id som visas
    # i "Sammanfattning" (t.ex. V86_2026-08-12_32_1), och
    # motsvarar filnamnet i data/races/.
    #

    engine = LearningEngine()
    engine.evaluate(game_id)
