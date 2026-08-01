"""
Chaos Insight
Race Model
Release 0.3.0
"""

from dataclasses import dataclass, field

from models.horse import Horse


@dataclass
class Race:

    race_id: str

    date: str

    track: str

    distance: int

    start_method: str

    horses: list[Horse] = field(default_factory=list)

    def add_horse(self, horse: Horse):

        self.horses.append(horse)

    def horse_count(self):

        return len(self.horses)