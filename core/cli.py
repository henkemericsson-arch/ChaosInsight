import typer

app = typer.Typer()

@app.command()
def version():
    print("Chaos Insight v0.2.1")

@app.command()
def analyze(subject: str):
    print(f"Analyzing {subject}...")

if __name__ == "__main__":
    app()
