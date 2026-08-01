"""
Chaos Insight
Core Engine
Release 0.2.1
"""

from datetime import datetime

from core.logger import Logger
from services.config_manager import ConfigManager
from analysis.knowledge_engine import KnowledgeEngine


class CoreEngine:

    def __init__(self):

        self.name = "Chaos Insight"

        self.version = "0.2.1"

        self.started = datetime.now()

        self.logger = Logger()

        self.config = ConfigManager()

        self.knowledge = KnowledgeEngine()

    def start(self):

        print("=" * 50)
        print(self.name)
        print(f"Version {self.version}")
        print("=" * 50)

        self.config.initialize()
        self.logger.write("Configuration loaded")

        self.knowledge.load()

        self.logger.write(
            f"Knowledge loaded "
            f"({self.knowledge.count()} parameters)"
        )

        self.logger.write(
            f"Knowledge categories: "
            f"{len(self.knowledge.categories())}"
        )

        self.logger.write(
            f"{self.name} {self.version} startar"
        )

        self.logger.write("Core Engine initierad")

        self.logger.write(
            f"Starttid: "
            f"{self.started.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        self.logger.write("Status: OK")

        print("=" * 50)