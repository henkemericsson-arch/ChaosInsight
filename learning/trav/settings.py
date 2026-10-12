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
# Automatisk justering (etapp 4, 005 avsnitt 5 och 18).
# TUNING_MIN_NEW_RACES   nya lopp sedan senaste justering (avkylning)
# TUNING_DAMPING         η: ny = gammal + η * (föreslagen - gammal)
# TUNING_STEP_CAP        högsta relativa ändring per justering
# TUNING_TOTAL_CAP       högsta relativa avstånd från baseline
# ROLLBACK_MIN_RACES     lopp med ny version innan återrullning prövas
# ROLLBACK_WINDOW        högst så många lopp räknas i uppföljningen
#
TUNING_MIN_NEW_RACES = 100
TUNING_DAMPING = 0.2
TUNING_STEP_CAP = 0.10
TUNING_TOTAL_CAP = 0.50
ROLLBACK_MIN_RACES = 50
ROLLBACK_WINDOW = 100

#
# Viktanalys (etapp 2a, 005 avsnitt 17).
# Färre lopp än WEIGHT_MIN_RACES_REPORT -> bara antalet redovisas.
# WEIGHT_RIDGE är straffet mot stora koefficienter; WEIGHT_BOOTSTRAP
# antalet omtagningar för koefficienternas konfidensintervall.
#
WEIGHT_MIN_RACES_REPORT = 40
WEIGHT_RIDGE = 1.0
WEIGHT_BOOTSTRAP = 60

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
