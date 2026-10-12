#
# Travspecifika inställningar för Learning Engine (adapter-lagret).
# Den generella analyskoden i learning/ känner inte till något härifrån
# - den får allt via parametrar.
#

#
# Vilka sparade strategier som räknas som samma modell. continuous
# och legacy delar exakt samma Total Score per häst (de skiljer sig
# bara i garderingsbredd), så de analyseras som en modell: KAMT v1.
#
MODEL_STRATEGIES = {
    "kamt_v1": ("continuous", "legacy"),
    "kamt_v2": ("kamt_v2",),
}

#
# Strategier som analyseras var för sig när det gäller vilka hästar
# som faktiskt valdes (täckning, missanalys). De väljer olika hästar
# trots att continuous/legacy delar Total Score.
#
COVERAGE_STRATEGIES = {
    "continuous": ("continuous",),
    "legacy": ("legacy",),
    "kamt_v2": ("kamt_v2",),
}

#
# Galoppbanor som av misstag kommit med i travflödet. Utesluts ur
# analysen tills de filtreras bort redan vid insamlingen. Jämförs
# skiftlägesoberoende som delsträng mot banans namn.
#
GALLOP_TRACKS = ("Bro Park",)

#
# Distansklasser (meter). (namn, högsta distans i klassen).
#
DISTANCE_CLASSES = (
    ("kort <=1700 m", 1700),
    ("medel 1701-2300", 2300),
    ("lång >2300 m", None),
)

#
# Underlagskrav från 005_Learning_Engine_Design.md avsnitt 5.
# Etapp 1 ändrar inget - siffrorna används bara för att visa hur
# långt datamängden är från vad automatisk justering kräver.
#
MIN_RACES_FOR_TUNING = 300

#
# Regimer: tidsperioder då systemet byggdes på ett visst sätt.
# Rapporten delas upp per regim så att lopp från före en större
# ändring inte blandas med lopp efter den.
#
# Format: (namn, första loppdatum som ingår, "ÅÅÅÅ-MM-DD").
# Måste vara sorterad stigande. Tom lista = en enda regim.
# Lägg till rader när större ändringar införs, t.ex.:
#   ("0.5.0 spik/lås via odds", "2026-10-09"),
#
REGIMES = []
