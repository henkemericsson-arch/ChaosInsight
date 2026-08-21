from config.bet_prices import ROW_PRICES, DEFAULT_ROW_PRICE


class SystemGenerator:
    #
    # Bygger ett spelsystemförslag utifrån rankade hästar
    # per lopp (Total Score från ScoreEngine), önskad
    # risknivå, antal spikar, antal lås och maximal
    # systemkostnad.
    #
    # Radpriset hämtas från config/bet_prices.py, baserat på
    # spelets typ (V85, V86, V5 osv), och motsvarar ATG:s
    # officiella priser.
    #
    # Tva garderingsprinciper stods, valbara via
    # coverage_strategy:
    #
    #   "continuous" (standard) - garderingen for ovriga lopp
    #   (utanfor spikar/las) skalar kontinuerligt med loppets
    #   kaosvarde (0-100), mellan ett min- och maxantal hastar
    #   per risknivå.
    #
    #   "legacy" - den ursprungliga principen: en fast
    #   garderingsniva per risknivå, plus en binar bonus (+1
    #   hast) om kaosvardet overstiger 60.
    #
    # Bada finns kvar sa att de kan genereras parallellt och
    # jamforas mot varandra over tid.
    #

    RISK_COVERAGE_RANGE = {
        "Låg": (2, 4),
        "Mellan": (2, 5),
        "Hög": (3, 7),
    }

    RISK_COVERAGE_LEGACY = {
        "Låg": 2,
        "Mellan": 3,
        "Hög": 5,
    }

    def generate(self, races, max_cost, risk, spikes, locks, game_type=None,
                 coverage_strategy="continuous"):
        row_price = ROW_PRICES.get(game_type, DEFAULT_ROW_PRICE)

        #
        # Sortera loppen efter Kaosvärde, stabilast först.
        # De stabilaste loppen är säkrast att spika/låsa.
        #
        sorted_races = sorted(
            races, key=lambda r: getattr(r, "kaosvarde", 0)
        )

        leg_selections = []

        for index, race in enumerate(sorted_races):

            ranked_horses = sorted(
                race.horses,
                key=lambda h: h.get_metric("total_score"),
                reverse=True,
            )

            if index < spikes:
                #
                # Spik: bara den högst rankade hästen.
                #
                chosen = ranked_horses[:1]
            elif index < spikes + locks:
                #
                # Lås: de två högst rankade hästarna.
                #
                chosen = ranked_horses[:2]
            else:
                kaosvarde = getattr(race, "kaosvarde", 0)

                if coverage_strategy == "legacy":
                    coverage = self._coverage_legacy(risk, kaosvarde)
                else:
                    coverage = self._coverage_continuous(risk, kaosvarde)

                chosen = ranked_horses[:coverage]

            leg_selections.append({
                "race": race,
                "horses": chosen,
            })

        total_cost = self._calculate_cost(leg_selections, row_price)

        #
        # Om kostnaden överstiger budgeten, dra ner
        # garderingar (utom spikar) tills systemet ryms.
        #
        while total_cost > max_cost and self._can_reduce(leg_selections, spikes, locks):
            self._reduce_widest_leg(leg_selections, spikes, locks)
            total_cost = self._calculate_cost(leg_selections, row_price)

        self._print_system(
            leg_selections, total_cost, max_cost, row_price, coverage_strategy
        )

        return leg_selections, total_cost

    def _coverage_continuous(self, risk, kaosvarde):
        min_coverage, max_coverage = self.RISK_COVERAGE_RANGE.get(risk, (2, 5))

        kaos = kaosvarde or 0
        kaos = max(0, min(kaos, 100))

        scaled = min_coverage + (max_coverage - min_coverage) * (kaos / 100)

        return round(scaled)

    def _coverage_legacy(self, risk, kaosvarde):
        coverage = self.RISK_COVERAGE_LEGACY.get(risk, 3)

        if (kaosvarde or 0) > 60:
            coverage += 1

        return coverage

    @staticmethod
    def _calculate_cost(leg_selections, row_price):
        rows = 1
        for leg in leg_selections:
            rows *= max(len(leg["horses"]), 1)

        return round(rows * row_price, 2)

    @staticmethod
    def _can_reduce(leg_selections, spikes, locks):
        for index, leg in enumerate(leg_selections):
            if index < spikes + locks:
                continue

            if len(leg["horses"]) > 1:
                return True
        return False

    @staticmethod
    def _reduce_widest_leg(leg_selections, spikes, locks):
        #
        # Ta bort den svagast rankade hästen från loppet
        # (utanför spikar/lås) som har flest hästar kvar.
        #
        candidates = [
            (index, leg)
            for index, leg in enumerate(leg_selections)
            if index >= spikes + locks and len(leg["horses"]) > 1
        ]

        if not candidates:
            return

        widest_index, widest_leg = max(
            candidates, key=lambda pair: len(pair[1]["horses"])
        )

        widest_leg["horses"].pop()

    def _print_system(self, leg_selections, total_cost, max_cost, row_price, coverage_strategy):
        print()
        print("=" * 60)
        print(f"Systemförslag ({coverage_strategy})")
        print("=" * 60)
        print(f"Radpris: {row_price} kr")

        #
        # Sorteras efter loppnummer bara for utskriften -
        # sjalva tilldelningen av spikar/las ovan bygger
        # fortfarande pa kaosvarde, inte loppordning.
        #
        for leg in sorted(
            leg_selections, key=lambda leg: leg["race"].race_number
        ):
            race = leg["race"]
            horse_names = ", ".join(
                f"{h.number}. {h.name}" for h in leg["horses"]
            )
            print(f"{race} (Kaosvärde: {getattr(race, 'kaosvarde', 0)})")
            print(f"  -> {horse_names}")

        print()
        print(f"Total systemkostnad: {total_cost} kr (budget: {max_cost} kr)")

        if total_cost > max_cost:
            print(
                "OBS: Systemet ryms inte inom budgeten även efter "
                "neddragning. Fler spikar/lås eller lägre risknivå krävs."
            )
