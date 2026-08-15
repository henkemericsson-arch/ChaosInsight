class SystemGenerator:

    #
    # Bygger ett spelsystemförslag utifrån rankade hästar
    # per lopp (Total Score från ScoreEngine), önskad
    # risknivå, antal spikar, antal lås och maximal
    # systemkostnad.
    #
    # OBS: Kostnad per rad är satt till 1 kr som ett
    # antagande (standard för de flesta ATG-flerloppsspel),
    # men detta bör verifieras mot riktig speldata innan
    # systemet används skarpt.
    #

    ROW_COST = 1

    RISK_COVERAGE = {
        "Låg": 2,
        "Mellan": 3,
        "Hög": 5,
    }

    def generate(self, races, max_cost, risk, spikes, locks):

        #
        # Sortera loppen efter Kaosvärde, stabilast först.
        # De stabilaste loppen är säkrast att spika/låsa.
        #

        sorted_races = sorted(
            races, key=lambda r: getattr(r, "kaosvarde", 0)
        )

        base_coverage = self.RISK_COVERAGE.get(risk
, 3)

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

                coverage = base_coverage

                kaosvarde = getattr(race, "kaosvarde", 0)

                if kaosvarde > 60:

                    #
                    # Kaoslopp - lägg till en extra
                    # gardering enligt KAMT-modellen.
                    #

                    coverage += 1

                chosen = ranked_horses[:coverage]

            leg_selections.append({
                "race": race,
                "horses": chosen,
            })

        total_cost = self._calculate_cost(leg_selections)

        #
        # Om kostnaden överstiger budgeten, dra ner
        # garderingar (utom spikar) tills systemet ryms.
        #

        while total_cost > max_cost and self._can_reduce(leg_selections, spikes, locks):

            self._reduce_widest_leg(leg_selections, spikes, locks)

            total_cost = self._calculate_cost(leg_selections)

        self._print_system(leg_selections, total_cost, max_cost)

        return leg_selections, total_cost

    def _calculate_cost(self, leg_selections):

        rows = 1

        for leg in leg_selections:
            rows *= max(len(leg["horses"]), 1)

        return rows * self.ROW_COST

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

    def _print_system(self, leg_selections, total_cost, max_cost):

        print()
        print("=" * 60)
        print("Systemförslag")
        print("=" * 60)

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
