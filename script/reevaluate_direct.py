"""
Kor Learning Engine direkt mot ett redan utvarderat system, utan
att ga via webbgranssnittets "redan utvarderat"-sparr - anvands
for att verifiera en fix utan att behova ett helt nytt,
outvarderat system.

Skriver INTE over den sparade filens outcome/payout permanent pa
nagot satt som skulle skilja sig fran en vanlig omvardering -
LearningEngine.evaluate() fungerar likadant har som via appen.

Kor fran projektroten:
    python script/reevaluate_direct.py <prediction_id>
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.learning_engine import LearningEngine


def main():
    if len(sys.argv) < 2:
        print("Anvandning: python script/reevaluate_direct.py <prediction_id>")
        return

    prediction_id = sys.argv[1]

    engine = LearningEngine()
    engine.evaluate(prediction_id)


if __name__ == "__main__":
    main()
