class AnalysisEngine:

    def __init__(self):

        self.modules = []

    def add_module(self, module):

        self.modules.append(module)

    def analyze(self, analysis_data):

        print()
        print("=" * 60)
        print("Analysis Engine")
        print("=" * 60)

        for module in self.modules:

            print(f"Kör {module.name}")

            module.analyze(analysis_data)

        return analysis_data