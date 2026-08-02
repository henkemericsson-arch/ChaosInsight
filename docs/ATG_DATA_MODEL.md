# Chaos Insight
## ATG Data Model

Syftet med detta dokument är att beskriva hur informationen hos ATG är organiserad och hur den ska motsvaras av Chaos Insights modeller.

--------------------------------------------------------

DATUM

↓

RaceDay

Innehåller:

- Datum
- Alla spel denna dag
- Banor
- Starttider
- Övrig information som gäller hela tävlingsdagen

↓

Game

Exempel:

- V75
- V86
- V64
- DD
- V4

Innehåller:

- Namn
- Bana
- Antal lopp
- Lista över lopp

↓

Race

Innehåller:

- Loppnummer
- Distans
- Startmetod
- Klass
- Startlista

↓

Horse

Innehåller:

- Namn
- Nummer
- Kusk
- Tränare
- Odds
- Skor
- Vagn
- Form
- Statistik

--------------------------------------------------------

Data som senare hämtas från andra källor

Weather
Forum
Experts
Market
Statistics
History

--------------------------------------------------------

Princip

ATG ansvarar endast för officiell tävlingsinformation.

Övrig information hämtas av AnalysisDataCollector från respektive specialiserad datakälla.