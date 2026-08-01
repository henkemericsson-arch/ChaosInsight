"""
Chaos Insight
Driver Model
Release 0.3.0
"""

from dataclasses import dataclass


@dataclass
class Driver:
    id: str
    name: str

    def to_dict(self):

        return {
            "id": self.id,
            "name": self.name
        }