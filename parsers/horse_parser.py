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

        age = horse_data.get("age")
        sex = horse_data.get("sex")

        return Horse(
            number=number,
            name=name,
            driver=driver,
            trainer=trainer,
            start_position=start_position,
            odds=odds,
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