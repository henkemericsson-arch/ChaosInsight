import math

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
    # Loppen sorteras efter kaosvärde (stabilast först) sa att
    # spik/las alltid hamnar pa de sakraste loppen - det ar dar
    # kombinatoriken vinner mest (en spik/las kostar bara x1 i
    # radantalet, medan ett brett lopp multiplicerar radantalet
    # rakt av). Ovriga lopps garderingsbredd skalar sedan med
    # loppets EGNA kaosvarde - jamna lopp far fardre platser,
    # kaotiska lopp far fler. Detta ar HELT ofrikopplat fran
    # risknivan (se nedan) och budgeten - kaosvardet ensamt
    # avgor totalbredden per lopp.
    #
    # Tva garderingsprinciper stods, valbara via
    # coverage_strategy:
    #
    #   "continuous" (standard) - bredden for ovriga lopp
    #   skalar kontinuerligt med loppets kaosvarde (0-100),
    #   mellan ett min- och maxantal hastar.
    #
    #   "legacy" - den ursprungliga principen: en fast
    #   garderingsniva, plus en binar bonus (+1 hast) om
    #   kaosvardet overstiger 60.
    #
    # Bada finns kvar sa att de kan genereras parallellt och
    # jamforas mot varandra over tid.
    #
    # Risknivan paverkar INTE totalbredden (och darmed inte
    # kostnaden) - det ar budgeten och kaosvardet som avgor hur
    # manga hastar som far plats. Risknivan avgor istallet HUR
    # den redan bestamda bredden fordelas: en andel av platserna
    # (se RISK_FAVORITE_RATIO) garanteras ga till genuina
    # favoritkandidater (lagst odds, med Total Score som
    # avgorande vid jamna odds - se _select_with_favorite_floor),
    # resten fylls av Total Score-rankning bland ovriga hastar -
    # dar analysens formaga att hitta icke-sjalvklara skrallar
    # slar igenom. Ju hogre risk, desto storre andel av platserna
    # lamnas oppna for den analysstyrda delen - och eftersom det
    # ar en ANDEL av en redan varierande bredd (inte ett fast
    # antal), vaxer utrymmet for skrallar naturligt med systemets
    # storlek utan nagon hardkodad siffra.
    #

    BASE_COVERAGE_RANGE = (2, 5)
    BASE_COVERAGE_LEGACY = 3

    RISK_FAVORITE_RATIO = {
        "Låg": 0.7,
        "Mellan": 0.5,
        "Hög": 0.3,
    }

    #
    # Hur stor oddsmarginal fran faltets basta odds som raknas
    # som en "genuin favoritkandidat". 1.4 = odds upp till 40%
    # hogre an favoritens far vara med och tavla om favorit-
    # platserna via Total Score. T.ex. med basta odds 1.72 racknas
    # allt upp till 2.41 som en genuin kandidat.
    #
    FAVORITE_ODDS_MARGIN = 1.4

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
                    coverage = self._coverage_legacy(kaosvarde)
                else:
                    coverage = self._coverage_continuous(kaosvarde)

                chosen = self._select_with_favorite_floor(race.horses, coverage, risk)

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

    def _coverage_continuous(self, kaosvarde):
        min_coverage, max_coverage = self.BASE_COVERAGE_RANGE
        kaos = kaosvarde or 0
        kaos = max(0, min(kaos, 100))
        scaled = min_coverage + (max_coverage - min_coverage) * (kaos / 100)
        return round(scaled)

    def _coverage_legacy(self, kaosvarde):
        coverage = self.BASE_COVERAGE_LEGACY
        if (kaosvarde or 0) > 60:
            coverage += 1
        return coverage

    @classmethod
    def _select_with_favorite_floor(cls, horses, coverage, risk):
        if coverage <= 0 or not horses:
            return []

        ratio = cls.RISK_FAVORITE_RATIO.get(risk, 0.5)
        favorite_slots = max(1, min(coverage, round(coverage * ratio)))

        ranked_by_score = sorted(
            horses, key=lambda h: h.get_metric("total_score"), reverse=True
        )

        with_odds = sorted(
            (h for h in horses if h.odds is not None), key=lambda h: h.odds
        )
        without_odds = [h for h in horses if h.odds is None]

        if with_odds:
            best_odds = with_odds[0].odds
            margin = best_odds * cls.FAVORITE_ODDS_MARGIN
            contenders = [h for h in with_odds if h.odds <= margin]
            rest_by_odds = [h for h in with_odds if h.odds > margin]
        else:
            contenders, rest_by_odds = [], []

        contender_numbers = {h.number for h in contenders}

        #
        # Bland de genuina favoritkandidaterna avgor Total Score
        # rangordningen - inte den rena oddssiffran.
        #
        favorites = [
            h for h in ranked_by_score if h.number in contender_numbers
        ][:favorite_slots]

        #
        # Rackte inte de genuina kandidaterna till, fylls resten
        # pa i strikt oddsordning - dar finns ingen verklig
        # konkurrens att lata Total Score avgora.
        #
        if len(favorites) < favorite_slots:
            needed = favorite_slots - len(favorites)
            favorites = favorites + rest_by_odds[:needed]
        if len(favorites) < favorite_slots:
            needed = favorite_slots - len(favorites)
            favorites = favorites + without_odds[:needed]

        favorite_numbers = {h.number for h in favorites}

        chosen = list(favorites)
        for horse in ranked_by_score:
            if len(chosen) >= coverage:
                break
            if horse.number in favorite_numbers:
                continue
            chosen.append(horse)

        return chosen

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
