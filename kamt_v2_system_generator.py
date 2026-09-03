"""
KAMT v2 - genererar ett fullstandigt skuggat system (spikar, las,
gardering per lopp) fran RaceAnalyzer:s sannolikhetsfordelningar,
genom att atervanda den redan befintliga SystemGenerator (samma
motor KAMT v1 anvander) - bara med KAMT v2:s sannolikheter som
indata istallet for KAMT v1:s Total Score.

ShadowHorse/ShadowRace kopierar (las-bara) alla falt fran de
riktiga Horse/Race-objekten som PredictionLogger.save() behover
for att kunna spara KAMT v2:s skuggsystem for utvardering pa
samma satt som de riktiga systemen - utan att nagonsin mutera
eller paverka de riktiga objekten.

Placerad har tillfalligt i projektroten - hor egentligen hemma i
modules/trav/ (Lager 3) enligt 003_Restructuring_Plan.md.
"""

from services.system_generator import SystemGenerator


class ShadowHorse:
    #
    # Duck-typad motsvarighet till models/horse.py - kopierar alla
    # falt PredictionLogger._leg_to_dict() lasar av, sa att KAMT
    # v2:s skuggsystem kan sparas for utvardering pa samma satt
    # som de riktiga systemen.
    #
    def __init__(self, number, name, odds, driver=None, trainer=None,
                 start_position=None, bet_percentage=None, shod_front=None,
                 shod_back=None, shoe_changed=None, sulky_changed=None,
                 cart_type=None, career_earnings=None, driver_win_pct=None,
                 trainer_win_pct=None, horse_win_pct=None):
        self.number = number
        self.name = name
        self.odds = odds
        self.driver = driver
        self.trainer = trainer
        self.start_position = start_position
        self.bet_percentage = bet_percentage
        self.shod_front = shod_front
        self.shod_back = shod_back
        self.shoe_changed = shoe_changed
        self.sulky_changed = sulky_changed
        self.cart_type = cart_type
        self.career_earnings = career_earnings
        self.driver_win_pct = driver_win_pct
        self.trainer_win_pct = trainer_win_pct
        self.horse_win_pct = horse_win_pct
        self._metrics = {}

    def set_metric(self, key, value):
        self._metrics[key] = value

    def get_metric(self, key):
        return self._metrics.get(key)

    @classmethod
    def from_real_horse(cls, horse):
        #
        # Bygger en ShadowHorse genom att kopiera fasta falt fran
        # en riktig Horse - las-bar kopia, ror aldrig originalet.
        #
        return cls(
            number=horse.number, name=horse.name, odds=horse.odds,
            driver=getattr(horse, "driver", None),
            trainer=getattr(horse, "trainer", None),
            start_position=getattr(horse, "start_position", None),
            bet_percentage=getattr(horse, "bet_percentage", None),
            shod_front=getattr(horse, "shod_front", None),
            shod_back=getattr(horse, "shod_back", None),
            shoe_changed=getattr(horse, "shoe_changed", None),
            sulky_changed=getattr(horse, "sulky_changed", None),
            cart_type=getattr(horse, "cart_type", None),
            career_earnings=getattr(horse, "career_earnings", None),
            driver_win_pct=getattr(horse, "driver_win_pct", None),
            trainer_win_pct=getattr(horse, "trainer_win_pct", None),
            horse_win_pct=getattr(horse, "horse_win_pct", None),
        )


class ShadowRace:
    #
    # Duck-typad motsvarighet till models/race.py - kopierar alla
    # falt PredictionLogger._leg_to_dict() lasar av.
    #
    def __init__(self, race_id, race_number, track, distance, start_method,
                 track_condition, horses, kaosvarde):
        self.race_id = race_id
        self.race_number = race_number
        self.track = track
        self.distance = distance
        self.start_method = start_method
        self.track_condition = track_condition
        self.horses = horses
        self.kaosvarde = kaosvarde

    def __repr__(self):
        return f"V{self.race_number} (KAMT v2)"

    @classmethod
    def from_real_race(cls, race, horses, kaosvarde):
        return cls(
            race_id=getattr(race, "race_id", None),
            race_number=race.race_number,
            track=getattr(race, "track", None),
            distance=getattr(race, "distance", None),
            start_method=getattr(race, "start_method", None),
            track_condition=getattr(race, "track_condition", None),
            horses=horses,
            kaosvarde=kaosvarde,
        )


def build_shadow_races(races, predictions_by_race):
    #
    # Bygger ShadowRace/ShadowHorse fran de riktiga loppens
    # hastar - alla falt kopieras oforandrade - men med KAMT v2:s
    # forutsagda sannolikhet som total_score, och ett kaosvarde
    # harlett fran sannolikhetsfordelningens spridning: 100 -
    # toppfavoritens sannolikhet.
    #
    shadow_races = []

    for race in races:
        probabilities = predictions_by_race.get(race.race_number)
        if not probabilities:
            continue

        shadow_horses = []
        for horse in race.horses:
            probability = probabilities.get(horse.number)
            if probability is None:
                continue

            shadow_horse = ShadowHorse.from_real_horse(horse)
            shadow_horse.set_metric("total_score", probability)
            shadow_horses.append(shadow_horse)

        if not shadow_horses:
            continue

        top_probability = max(probabilities.values())
        kaosvarde = round(100 - top_probability, 1)

        shadow_races.append(ShadowRace.from_real_race(race, shadow_horses, kaosvarde))

    return shadow_races


def generate_shadow_system(races, predictions_by_race, max_cost, risk, spikes, locks, game_type=None):
    #
    # Genererar ett fullstandigt KAMT v2-skuggsystem genom att
    # atervanda den befintliga, redan testade SystemGenerator -
    # bara med KAMT v2:s sannolikheter som indata. Returnerar
    # (leg_selections, total_cost), precis som SystemGenerator.
    # generate() gor for det riktiga systemet.
    #
    # Returnerar ([], 0) om inget lopp kunde simuleras av
    # RaceAnalyzer (t.ex. helt ny bana/hastar utan historik).
    #
    shadow_races = build_shadow_races(races, predictions_by_race)

    if not shadow_races:
        return [], 0

    generator = SystemGenerator()
    return generator.generate(
        races=shadow_races, max_cost=max_cost, risk=risk,
        spikes=spikes, locks=locks, game_type=game_type,
        coverage_strategy="continuous",
    )
