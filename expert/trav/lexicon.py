import re

#
# Travspecifik ordlista och radmonster for expert/interpreter.py.
# Ren data - tolkarkarnan ar generell och far den har som parameter,
# sa att en annan domän kan lagga en egen lexicon utan att andra koden.
#
# Signaltyper: vinnare, spik, skrall, vardet, med, avrad (fria cues)
# samt system, rank, tier_a/b/c (fran strukturerade rader).
#

I = re.IGNORECASE

# --- Loppmarken ------------------------------------------------------
# "V85-3", "GS75-2", "DD-1", "V86 4", "Avd 3", "Lopp 3", "Avdelning 3"
LEG_LABEL = r"(?:(?:V\d{1,2}|GS75|DD|LD|V5|V4|V3)\s*[-–]\s*|(?:avd(?:elning)?\.?|lopp)\s*)(\d{1,2})\b"
LEG_HEADER = re.compile(r"^\s*" + LEG_LABEL, I)
LEG_ANYWHERE = re.compile(LEG_LABEL, I)

# Systemtabellrad: "V85-3 | 1,4,5" eller "GS75-2 | 12 Florio I.T."
TABLE_ROW = re.compile(
    r"^\s*" + LEG_LABEL + r"\s*\|\s*(\d{1,2}(?:\s*,\s*\d{1,2})*)", I
)

# Tabellrad utan loppmarke: "3 | 8 Clarissa 4 7" (forsta cellen = avdelning)
TABLE_ROW_BARE = re.compile(r"^\s*(\d{1,2})\s*\|\s*(\d{1,2}\b[^|]*)(?:\|[^|]*)?$")

# Kategorirubriker ("Omgangens Bank:") och poster under dem ("8 Clarissa (V85-3) ...")
CATEGORY_LINES = [
    ("spik", re.compile(r"^\s*omg[a\u00e5]ngens\s+(?:bank|spik)\b", I)),
    ("skrall", re.compile(r"^\s*omg[a\u00e5]ngens\s+(?:korsdrag|skr[a\u00e4]ll)", I)),
    ("avrad", re.compile(r"^\s*omg[a\u00e5]ngens\s+[o\u00f6]verstreckade", I)),
]
ENTRY_WITH_LEG = re.compile(
    r"^\s*[\u201d\u201c\"'\u00bb\u00ab]*\s*(\d{1,2})\s+[^()|]{2,40}?\s*\(\s*(?:V\d{1,2}|GS75|DD|LD)\s*[-\u2013]\s*(\d{1,2})\s*\)", I)

# --- Strukturerade rader -------------------------------------------------
# "RANK: 4-1-6-7"  "Rankingen: A: 2 B: 1,4,5 C: 11,12"
RANK_LINE = re.compile(r"^\s*rank(?:ing(?:en)?)?\s*:\s*(.+)$", I)
TIER_PART = re.compile(r"\b([ABC])\s*:\s*([\d,\s\-]+)", re.IGNORECASE)
NUMBER_LIST = re.compile(r"\d{1,2}")

# "Min vinnare: 2 Cold Blaze", "Skrallen: 4 Herkules", "Spik: 5", "Streckar: 5, 6, 9"
LABELED_LINES = [
    ("vinnare", re.compile(r"^\s*(?:min\s+vinnare|vinnare|vinnaren)\s*:\s*(.+)$", I)),
    ("skrall", re.compile(r"^\s*skr[aä]llen?\s*:\s*(.+)$", I)),
    ("spik", re.compile(r"^\s*spik(?:ar|en)?\s*:\s*(.+)$", I)),
    ("system", re.compile(r"^\s*(?:streckar|system|h[aä]star|med)\s*:\s*(.+)$", I)),
    ("vardet", re.compile(r"^\s*(?:v[aä]rdet|spelv[aä]rd(?:a)?|streckv[aä]rd(?:a)?)\s*:\s*(.+)$", I)),
    ("avrad", re.compile(r"^\s*(?:avr[aå]der|bort|stryk)\s*:\s*(.+)$", I)),
]

# --- Fria cues i prosa ---------------------------------------------------
# (signal, monster). Matchas per mening; entiteter i samma mening far signalen.
CUES = [
    ("spik", re.compile(
        r"\bspik(?:en|ar|ad|as|ade|ning)?\b|\bspikf[o\u00f6]rslag\b|\bspikkandidat\b|\bsingelstreck\b|\bbanker\b|\bj[aä]g\s+spikar\b", I)),
    ("vinnare", re.compile(
        r"\bmin\s+vinnare\b|\bska\s+vinna\b|\bklar\s+vinnare\b|\bvinnarkandidat\b|\bsj[aä]lvskriven\b|\bstenklar\b", I)),
    ("skrall", re.compile(
        r"\bskr[aä]ll(?:en|bud|kandidat)?\b|\boutsider\b|\b[oö]verraskare\b|\bchansartad\b", I)),
    ("vardet", re.compile(
        r"\bspelv[aä]rd(?:ig|a)?\b|\bstreckv[aä]rd(?:ig|a)?\b|\bunderv[aä]rderad\b|\bv[aä]rdeh[aä]st\b", I)),
    ("med", re.compile(
        r"\bgarder(?:ing|ar|a|ingsh[a\u00e4]st)\b|\bpassar\s+vi\b|\bstreckas\b|\bstr[oö]ms\b|\bb[oö]r\s+med\b|\bh[oö]r\s+med\b|\bm[aå]ste\s+med\b|\bing[aå]r\s+i\s+systemet\b|\balternativ\b", I)),
    ("avrad", re.compile(
        r"\bavr[aå]der\b|\b[oö]verspelad\b|\b[oö]verstreckad\b|\bhoppa\s+[oö]ver\b|\bl[aä]mnas\s+utanf[oö]r\b", I)),
]

# Negation direkt fore en cue (inom fa tecken): "ingen spik", "inte med".
NEGATION = re.compile(r"\b(?:ingen|inget|inte|ej|knappast|aldrig)\b[^.!?]{0,20}$", I)
# Negerad cue: spik/vinnare/vardet/skrall faller bort, med -> avrad.
NEGATION_MAP = {"med": "avrad"}

# Siffer-/ordhanvisningar till hast: "nr 5", "5:an", "femman"
NUMBER_WORDS = {
    "ettan": 1, "tvåan": 2, "trean": 3, "fyran": 4, "femman": 5, "sexan": 6,
    "sjuan": 7, "åttan": 8, "nian": 9, "tian": 10, "elvan": 11, "tolvan": 12,
    "trettonan": 13, "fjortonan": 14, "femtonan": 15,
}
NR_REFERENCE = re.compile(r"\b(?:nr|nummer|häst(?:nummer)?)\.?\s*(\d{1,2})\b|\b(\d{1,2}):an\b", I)

# --- Poangsattning (expert/scoring.py) -------------------------------------
# Stod per signal (0..3 efter tak). Data, satt av utvecklaren.
SIGNAL_WEIGHTS = {
    "spik": 3.0,
    "vinnare": 3.0,
    "tier_a": 2.0,
    "rank_top": 2.0,     # skalar med rangordning (1:a=full, sista=0)
    "system": 1.0,
    "tier_b": 1.0,
    "vardet": 1.0,
    "skrall": 1.0,
    "med": 1.0,
    "tier_c": 0.3,
    "avrad": -2.0,
}
SUPPORT_CAP = 3.0

# Ord som en artikels text/adress ska innehalla for att galla en viss speltyp
# (jamfors utan mellanslag/bindestreck). Okand speltyp: speltypens eget namn.
GAME_TYPE_TOKENS = {
    "GS75": ("gs75", "grandslam75"),
    "DD": ("dd", "dagensdubbel"),
}
