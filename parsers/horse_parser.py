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
