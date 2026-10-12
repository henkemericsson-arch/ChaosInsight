#
# Etapp 2a: lägger trösklarna för viktanalysen i learning/trav/settings.py.
# Idempotent. Körs från projektroten:  python script/patch_weight_analysis.py
#
import sys

PATH = "learning/trav/settings.py"
with open(PATH, encoding="utf-8") as f:
    text = f.read()

if "WEIGHT_MIN_RACES_REPORT" in text:
    print("settings: redan gjort")
    sys.exit(0)

anchor = "MIN_RACES_FOR_TUNING = 300\n"
if text.count(anchor) != 1:
    print("settings: KRÄVER HANDPÅLÄGGNING (ankare hittades", text.count(anchor), "gånger)")
    sys.exit(1)

addition = anchor + """
#
# Viktanalys (etapp 2a, 005 avsnitt 17).
# Färre lopp än WEIGHT_MIN_RACES_REPORT -> bara antalet redovisas.
# WEIGHT_RIDGE är straffet mot stora koefficienter; WEIGHT_BOOTSTRAP
# antalet omtagningar för koefficienternas konfidensintervall.
#
WEIGHT_MIN_RACES_REPORT = 40
WEIGHT_RIDGE = 1.0
WEIGHT_BOOTSTRAP = 60
"""
with open(PATH, "w", encoding="utf-8") as f:
    f.write(text.replace(anchor, addition, 1))
print("settings: patchad")
