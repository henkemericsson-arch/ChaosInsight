p = "CHANGELOG.md"
s = open(p, encoding="utf-8").read()

if "## Unreleased" in s:
    print("Unreleased finns redan - ingen ändring.")
else:
    block = """## Unreleased

- Strukna hästar filtreras bort redan vid parsning (RaceParser) och odds 0 behandlas som struken i SystemGenerator.
- Lås väljs nu som de två främsta favoriterna enligt odds, rankade på summan av deras Total Score (samma princip som spikar).
- KAMT v2: hästar utan sannolikhet från RaceAnalyzer tappas inte längre, de får ett lågt standardvärde så att favoriter alltid kan bli spik, lås eller gardering.

"""
    i = s.find("\n## ")
    s = s[:i + 1] + block + s[i + 1:] if i != -1 else s + "\n" + block
    open(p, "w", encoding="utf-8").write(s)
    print("CHANGELOG uppdaterad.")
