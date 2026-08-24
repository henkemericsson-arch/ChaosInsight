class Horse:

    def __init__(
        self,
        number,
        name,
        driver="",
        trainer="",
        start_position=None,
        odds=None,
        bet_percentage=None,
        odds_trend=None,
        age=None,
        sex=None,
        driver_win_pct=None,
        driver_starts=None,
        trainer_win_pct=None,
        trainer_starts=None,
        horse_win_pct=None,
        horse_starts=None,
        shod_front=None,
        shod_back=None,
        shoe_changed=None,
        sulky_changed=None,
        cart_type=None,
        career_earnings=None,
    ):
        self.number = number
        self.name = name

        self.driver = driver
        self.trainer = trainer

        self.start_position = start_position
        self.odds = odds
        self.bet_percentage = bet_percentage
        self.odds_trend = odds_trend
        self.age = age
        self.sex = sex

        #
        # Aktuell form (innevarande/senaste säsong),
        # baserat på ATG:s statistics.years-data.
        #
        self.driver_win_pct = driver_win_pct
        self.driver_starts = driver_starts
        self.trainer_win_pct = trainer_win_pct
        self.trainer_starts = trainer_starts
        self.horse_win_pct = horse_win_pct
        self.horse_starts = horse_starts

        #
        # Skoning och utrustning.
        #
        self.shod_front = shod_front
        self.shod_back = shod_back
        self.shoe_changed = shoe_changed
        self.sulky_changed = sulky_changed

        #
        # Vagnstyp: "Vanlig", "Hybrid" eller "Amerikansk"
        # (ATG:s sulky.type.text). None om ej rapporterat.
        #
        self.cart_type = cart_type

        #
        # Hästens totala intjänade prispengar (karriär),
        # fran ATG:s horse.money. Anges i kr.
        #
        self.career_earnings = career_earnings

        self.metrics = {}
        self.score = 0.0

    def set_metric(self, key, value):
        self.metrics[key] = value

    def get_metric(self, key):
        return self.metrics.get(key, 0)

    def __repr__(self):
        return f"<Horse {self.number} {self.name}>"

