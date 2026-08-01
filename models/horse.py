"""
Chaos Insight
Horse Model
Release 0.3.0
"""

from dataclasses import dataclass

from models.driver import Driver
from models.trainer import Trainer


@dataclass
class Horse:
    id: str
    number: int
    name: str
    driver: Driver
    trainer: Trainer

    def to_dict(self):

        return {

            "id": self.id,

            "number": self.number,

            "name": self.name,

            "driver": self.driver.to_dict(),

            "trainer": self.trainer.to_dict()

        }