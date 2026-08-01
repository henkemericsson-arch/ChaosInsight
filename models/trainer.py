"""
Chaos Insight
Trainer Model
Release 0.3.0
"""

from dataclasses import dataclass


@dataclass
class Trainer:
    id: str
    name: str

    def to_dict(self):

        return {
            "id": self.id,
            "name": self.name
        }