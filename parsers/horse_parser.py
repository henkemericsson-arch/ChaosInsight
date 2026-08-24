class HorseParser:

    def parse(self, start_data):
        #
        # Tar emot rådata för en start (en häst i ett lopp)
        # från ATG:s races/starts-struktur och bygger ett
        # Horse-objekt.
        #
        from models.horse import Horse

        horse_data = start_data.get("horse") or {}
        driver_data = start_data.get("driver") or {}
        trainer_data = horse_data.get("trainer") or {}

        number = start_data.get("number")
        name = horse_data.get("name", "")
        driver = self._full_name(driver_data)
        trainer = self._full_name(trainer_data)

        start_position = start_data.get("postPosition")
        odds = self._extract_odds(start_data)
        bet_percentage = self._extract_bet_percentage(start_data)
        odds_trend = self._extract_odds_trend(start_data)

        age = horse_data.get("age")
        sex = horse_data.get("sex")
        driver_win_pct, driver_starts = self._extract_form(driver_data)
        trainer_win_pct, trainer_starts = self._extract_form(trainer_data)
        horse_win_pct, horse_starts = self._extract_form(horse_data)

        shod_front, shod_back, shoe_changed = self._extract_shoes(horse_data)
        sulky_changed = self._extract_sulky_changed(horse_data)
        cart_type = self._extract_cart_type(horse_data)
        career_earnings = horse_data.get("money")

        return Horse(
            number=number,
            name=name,
            driver=driver,
            trainer=trainer,
            start_position=start_position,
            odds=odds,
            bet_percentage=bet_percentage,
            odds_trend=odds_trend,
            age=age,
            sex=sex,
            driver_win_pct=driver_win_pct,
            driver_starts=driver_starts,
            trainer_win_pct=trainer_win_pct,
            trainer_starts=trainer_starts,
            horse_win_pct=horse_win_pct,
            horse_starts=horse_starts,
            shod_front=shod_front,
            shod_back=shod_back,
            shoe_changed=shoe_changed,
            sulky_changed=sulky_changed,
            cart_type=cart_type,
            career_earnings=career_earnings,
        )

    @staticmethod
    def _full_name(person_data):
        first_name = person_data.get("firstName", "")
        last_name = person_data.get("lastName", "")

        full_name = f"{first_name} {last_name}".strip()

        if full_name:
            return full_name

        return person_data.get("shortName", "")

    @staticmethod
    def _extract_odds(start_data):
        pools = start_data.get("pools") or {}
        vinnare_pool = pools.get("vinnare") or {}

        raw_odds = vinnare_pool.get("odds")
        if raw_odds is None:
            return None

        #
        # ATG använder 9999 som sentinelvärde för "inga
        # odds satta", inte ett riktigt odds.
        #
        if raw_odds == 9999:
            return None

        #
        # ATG anger odds i hundradelar,
        # t.ex. 2648 motsvarar 26.48 i odds.
        #
        return round(raw_odds / 100, 2)

    @staticmethod
    def _extract_bet_percentage(start_data):
        #
        # Streckprocent hämtas från flerloppsspelets pool
        # (t.ex. V86). Poolnamnet varierar per speltyp, så
        # vi letar igenom alla pooler efter en som har
        # betDistribution. Värdet anges i hundradelar av
        # procent, t.ex. 7215 motsvarar 72.15 %.
        #
        pools = start_data.get("pools") or {}

        for pool in pools.values():
            if isinstance(pool, dict) and "betDistribution" in pool:
                raw_value = pool.get("betDistribution")

                if raw_value is None:
                    return None

                return round(raw_value / 100, 2)

        return None

    @staticmethod
    def _extract_odds_trend(start_data):
        pools = start_data.get("pools") or {}

        for pool in pools.values():
            if isinstance(pool, dict) and "trend" in pool:
                return pool.get("trend")

        return None

    @staticmethod
    def _extract_form(person_or_horse_data):
        #
        # Hämtar aktuell form (vinstprocent och antal
        # starter) från statistics.years, baserat på det
        # senaste tillgängliga året. Funkar likadant för
        # kusk, tränare och häst, som alla har samma
        # statistics-struktur i ATG:s rådata.
        #
        years = (
            person_or_horse_data.get("statistics", {}).get("years", {})
        )

        if not years:
            return None, None

        latest_year = max(years.keys())
        year_stats = years[latest_year]

        starts = year_stats.get("starts")
        if not starts:
            return None, starts

        wins = year_stats.get("placement", {}).get("1", 0)
        win_pct = round((wins / starts) * 100, 1)

        return win_pct, starts

    @staticmethod
    def _extract_shoes(horse_data):
        shoes = horse_data.get("shoes") or {}

        if not shoes.get("reported"):
            return None, None, None

        front = shoes.get("front", {})
        back = shoes.get("back", {})

        shod_front = front.get("hasShoe")
        shod_back = back.get("hasShoe")

        shoe_changed = bool(
            front.get("changed") or back.get("changed")
        )

        return shod_front, shod_back, shoe_changed

    @staticmethod
    def _extract_sulky_changed(horse_data):
        sulky = horse_data.get("sulky") or {}

        if not sulky.get("reported"):
            return None

        type_changed = sulky.get("type", {}).get("changed", False)
        colour_changed = sulky.get("colour", {}).get("changed", False)

        return bool(type_changed or colour_changed)

    @staticmethod
    def _extract_cart_type(horse_data):
        #
        # Vagnstyp, t.ex. "Vanlig", "Hybrid" eller
        # "Amerikansk" (ATG:s sulky.type.text).
        #
        sulky = horse_data.get("sulky") or {}

        if not sulky.get("reported"):
            return None

        return sulky.get("type", {}).get("text")

