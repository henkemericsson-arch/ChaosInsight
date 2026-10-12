from dataclasses import dataclass, asdict
from typing import Optional

#
# En tolkad uppgift fran en expertkalla: "kalla X sager Y om hast Z i
# lopp N". Ren fakta - ingen bedomning av om tipset ar bra. Poangsattning
# gors av expert/scoring.py (och sedan ExpertAnalyzer).
#
# Signaltyper (se expert/trav/lexicon.py for hur de kanns igen):
#   vinnare, spik, skrall, system, rank, tier_a, tier_b, tier_c,
#   med, vardet, avrad
#


@dataclass
class ExpertTip:
    source: str
    leg: int
    horse_number: int
    signal: str
    horse_name: Optional[str] = None
    rank: Optional[int] = None
    rank_of: Optional[int] = None
    confidence: float = 1.0

    def to_dict(self):
        return asdict(self)
