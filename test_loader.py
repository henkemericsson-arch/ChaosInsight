from services.data_loader import DataLoader

loader = DataLoader()

race = loader.load_json("races/demo_race.json")

print(race)
print()

for horse in race.horses:
    print(horse)
