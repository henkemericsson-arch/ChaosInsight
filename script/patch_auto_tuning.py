#
# Kopplar automatisk justering till Learning Engines utvärdering
# (005 avsnitt 18.9). Idempotent. Körs från projektroten:
#   python script/patch_auto_tuning.py
# Allt eller inget: om ett ankare inte hittas skrivs ingen fil.
#
import sys

P = "services/learning_engine.py"
with open(P, encoding="utf-8") as f:
    text = f.read()

edits = [
    ("import",
     "from learning.trav.auto_hook import after_evaluation",
     "from foundation.run_info import dump_metrics\n",
     "from foundation.run_info import dump_metrics\nfrom learning.trav.auto_hook import after_evaluation\n"),
    ("anrop",
     "after_evaluation()",
     "        self._print_report(prediction, outcome)\n        return outcome\n",
     "        self._print_report(prediction, outcome)\n\n"
     "        #\n"
     "        # Automatisk justering (005 avsnitt 18.9): gör ingenting om den\n"
     "        # är avstängd, körs i egen tråd och kan aldrig påverka utvärderingen.\n"
     "        #\n"
     "        after_evaluation()\n"
     "        return outcome\n"),
]

problems = False
for label, marker, old, new in edits:
    if marker in text:
        print(f"  {label}: redan gjort")
        continue
    if text.count(old) != 1:
        print(f"  {label}: KRÄVER HANDPÅLÄGGNING (ankare hittades {text.count(old)} gånger)")
        problems = True
        continue
    text = text.replace(old, new, 1)
    print(f"  {label}: patchad")

if problems:
    print("Inget skrevs.")
    sys.exit(1)
with open(P, "w", encoding="utf-8") as f:
    f.write(text)
print("OK")
