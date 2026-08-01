"""
Chaos Insight
Logger
Release 0.2.1
"""

import os
from datetime import datetime


class Logger:

    def __init__(self):

        self.log_folder = "logs"

        os.makedirs(self.log_folder, exist_ok=True)

        self.log_file = os.path.join(
            self.log_folder,
            "chaosinsight.log"
        )

    def write(self, message):

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        line = f"[{timestamp}] {message}"

        print(line)

        with open(
            self.log_file,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(line + "\n")