import typer

from core.controller import Controller

app = typer.Typer()


@app.command()
def start():

    controller = Controller()
    controller.run()
