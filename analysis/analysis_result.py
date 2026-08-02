from dataclasses import dataclass


@dataclass
class AnalysisResult:
    module: str
    score: float
    weight: float = 1.0
    confidence: float = 1.0
    reason: str = ""