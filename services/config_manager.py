"""
Chaos Insight
Configuration Manager
Release 0.2.0
"""

import json
import os


class ConfigManager:

    def __init__(self):

        self.config_path = "config"

        self.files = {
            "application": "application.json",
            "logging": "logging.json"
        }

    def initialize(self):

        os.makedirs(self.config_path, exist_ok=True)

        self._create_application()

        self._create_logging()

    def _create_application(self):

        filename = os.path.join(
            self.config_path,
            self.files["application"]
        )

        if not os.path.exists(filename):

            data = {

                "name": "Chaos Insight",

                "version": "0.2.0"

            }

            with open(filename, "w", encoding="utf-8") as f:

                json.dump(data, f, indent=4)

    def _create_logging(self):

        filename = os.path.join(
            self.config_path,
            self.files["logging"]
        )

        if not os.path.exists(filename):

            data = {

                "enabled": True,

                "level": "INFO"

            }

            with open(filename, "w", encoding="utf-8") as f:

                json.dump(data, f, indent=4)