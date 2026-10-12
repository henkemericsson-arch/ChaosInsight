"""ShadowHorse får samma `metrics`-attribut som models/horse.Horse,
så att PredictionLogger kan läsa horse.metrics även för skuggsystem."""
import sys

PATH = "kamt_v2_system_generator.py"
with open(PATH, encoding="utf-8") as f:
    src = f.read()

if "self._metrics" not in src:
    print("Redan patchad:", PATH)
    sys.exit(0)

old = [("self._metrics = {}", "self.metrics = {}"),
       ("self._metrics[key] = value", "self.metrics[key] = value"),
       ("return self._metrics.get(key)", "return self.metrics.get(key)")]
for a, _ in old:
    if src.count(a) != 1:
        print("Kräver handpåläggning:", a, "förekommer", src.count(a), "gånger")
        sys.exit(1)
for a, b in old:
    src = src.replace(a, b)
with open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("Patchad:", PATH)
