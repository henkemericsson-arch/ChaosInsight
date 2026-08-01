"""
Chaos Insight
Knowledge Engine
Release 0.2.1
"""

import json
import os


class KnowledgeEngine:

    def __init__(self):

        self.base_path = "knowledge"

        self.parameters = {}

        self.ignore_dirs = {
            "schema",
            "__pycache__"
        }

    def load(self):

        self.parameters.clear()

        for root, dirs, files in os.walk(self.base_path):

            dirs[:] = [
                d for d in dirs
                if d not in self.ignore_dirs
            ]

            for file in files:

                if not file.endswith(".json"):
                    continue

                filename = os.path.join(root, file)

                try:

                    with open(
                        filename,
                        "r",
                        encoding="utf-8"
                    ) as f:

                        parameter = json.load(f)

                    parameter_id = parameter.get("id")

                    if parameter_id:

                        self.parameters[
                            parameter_id
                        ] = parameter

                except Exception as e:

                    print(
                        f"KnowledgeEngine: "
                        f"Kunde inte läsa {filename}"
                    )

                    print(e)

    def count(self):

        return len(self.parameters)

    def get(self, parameter_id):

        return self.parameters.get(parameter_id)

    def get_all(self):

        return self.parameters

    def categories(self):

        categories = set()

        for parameter in self.parameters.values():

            category = parameter.get("category")

            if category:

                categories.add(category)

        return sorted(categories)