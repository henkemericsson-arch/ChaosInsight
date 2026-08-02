import typer

from analysis.horse_analysis import HorseAnalysis
from analysis.race_analysis import RaceAnalysis

app = typer.Typer()


@app.command()
def version():
    print("Chaos Insight v0.3")


@app.command()
def horse(name: str):
    analyzer = HorseAnalysis()
    analyzer.analyze(name)


@app.command()
def race(file: str):
    analyzer = RaceAnalysis()
    analyzer.analyze(file)


if __name__ == "__main__":
    app()
