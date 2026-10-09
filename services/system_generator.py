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
    # SPIK- OCH LASVAL: bygger pa principen att marknaden
    # (odds) och analysen (Total Score) bor bekrafta varandra
    # for de mest sakra valen i systemet. Varje lopps
    # marknadsfavorit (lagst odds) rangordnas mot ovriga lopps
    # favoriter efter Total Score - det lopp dar favoriten har
    # HOGST Total Score bland alla lopps favoriter blir spikat,
    # och sjalva spiken ar DEN favoriten (inte nodvandigtvis
    # loppets egen Total Score-vinnare). Nasta lopp/lopp i samma
    # rangordning blir last, dar favoriten garanterat ingar plus
    # basta ovriga hast efter Total Score. Lopp utan oddsdata
    # (extremt ovanligt) faller tillbaka pa ren Total Score-
    # ranking, som tidigare.
    #
    # OVRIGA LOPPS GARDERINGSBREDD skalar sedan med respektive
    # lopps EGNA kaosvarde - jamna lopp far fardre platser,
    # kaotiska lopp far fler. Detta ar helt ofrikopplat fran
    # risknivan och budgeten - kaosvardet ensamt avgor
    # totalbredden per lopp.
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
    # kostnaden) for den ovriga garderingen - det ar budgeten
    # och kaosvardet som avgor hur manga hastar som far plats.
    # Risknivan avgor istallet HUR den redan bestamda bredden
    # fordelas: en andel av platserna (se RISK_FAVORITE_RATIO)
    # garanteras ga till genuina favoritkandidater (lagst odds,
    # med Total Score som avgorande vid jamna odds - se
    # _select_with_favorite_floor), resten fylls av Total
    # Score-rankning bland ovriga hastar.
    #

    BASE_COVERAGE_RANGE = (2, 5)
    BASE_COVERAGE_LEGACY = 3

    RISK_FAVORITE_RATIO = {
        "Låg": 0.5,
        "Mellan": 0.3,
        "Hög": 0.1,
    }

    #
    # Hur stor oddsmarginal fran faltets basta odds som raknas
    # som en "genuin favoritkandidat" (anvands for OVRIG
    # gardering, inte for spik/las - dar anvands alltid den
    # exakta lagst-oddsade hasten som favorit, utan marginal).
    #
    FAVORITE_ODDS_MARGIN = 1.4

    def generate(self, races, max_cost, risk, spikes, locks, game_type=None,
                 coverage_strategy="continuous"):
        row_price = ROW_PRICES.get(game_type, DEFAULT_ROW_PRICE)

        #
        # SPIK: rangordna lopp efter deras marknadsfavorits Total
        # Score - avgor vilka lopp som blir spikade. Lopp utan
        # oddsdata alls (extremt ovanligt) hamnar sist i
        # prioritetsordningen, sorterade pa kaosvarde.
        #
        races_with_favorite = []
        races_without_favorite = []

        for race in races:
            favorite = self._find_favorite(race.horses)
            if favorite is not None:
                races_with_favorite.append((race, favorite))
            else:
                races_without_favorite.append(race)

        races_with_favorite.sort(
            key=lambda pair: pair[1].get_metric("total_score") or 0,
            reverse=True,
        )
        races_without_favorite.sort(key=lambda r: getattr(r, "kaosvarde", 0))

        spike_priority_list = list(races_with_favorite)
        spike_priority_list += [(race, None) for race in races_without_favorite]

        spike_entries = spike_priority_list[:spikes]
        races_after_spikes = [race for race, _ in spike_priority_list[spikes:]]

        leg_selections = []

        for race, favorite in spike_entries:
            if favorite is not None:
                #
                # Spik: marknadens favorit i det lopp dar den
                # favoriten har hogst Total Score jamfort med
                # ovriga lopps favoriter.
                #
                chosen = [favorite]
            else:
                ranked_horses = sorted(
                    race.horses,
                    key=lambda h: h.get_metric("total_score"),
                    reverse=True,
                )
                chosen = ranked_horses[:1]

            leg_selections.append({"race": race, "horses": chosen})

        #
        # LAS: samma princip som spik, men med TVA favoriter per
        # lopp (de tva lagst-oddsade hastarna) istallet for en.
        # Rangordnas efter SUMMAN av bada favoriternas Total Score
        # - de lopp (bland de som inte redan spikats) dar paret har
        # starkast sammanlagt analysstod blir last.
        #
        races_with_pair = []
        races_without_pair = []

        for race in races_after_spikes:
            pair = self._find_top_two_by_odds(race.horses)
            if pair is not None:
                summed_score = sum(h.get_metric("total_score") or 0 for h in pair)
                races_with_pair.append((race, pair, summed_score))
            else:
                races_without_pair.append(race)

        races_with_pair.sort(key=lambda triple: triple[2], reverse=True)
        races_without_pair.sort(key=lambda r: getattr(r, "kaosvarde", 0))

        lock_priority_list = [(race, pair) for race, pair, _ in races_with_pair]
        lock_priority_list += [(race, None) for race in races_without_pair]

        lock_entries = lock_priority_list[:locks]
        remaining_races = [race for race, _ in lock_priority_list[locks:]]

        for race, pair in lock_entries:
            if pair is not None:
                #
                # Las: de tva favoriterna (lagst odds) i det lopp
                # dar paret har starkast sammanlagt Total Score
                # jamfort med ovriga aterstaende lopps par.
                #
                chosen = pair
            else:
                ranked_horses = sorted(
                    race.horses,
                    key=lambda h: h.get_metric("total_score"),
                    reverse=True,
                )
                chosen = ranked_horses[:2]

            leg_selections.append({"race": race, "horses": chosen})

        remaining_races_sorted = sorted(
            remaining_races, key=lambda r: getattr(r, "kaosvarde", 0)
        )

        for race in remaining_races_sorted:
            kaosvarde = getattr(race, "kaosvarde", 0)

            if coverage_strategy == "legacy":
                coverage = self._coverage_legacy(kaosvarde)
            else:
                coverage = self._coverage_continuous(kaosvarde)

            chosen = self._select_with_favorite_floor(race.horses, coverage, risk)

            leg_selections.append({"race": race, "horses": chosen})

        total_cost = self._calculate_cost(leg_selections, row_price)

        #
        # Om kostnaden överstiger budgeten, dra ner
        # garderingar (utom spikar/las) tills systemet ryms.
        #
        while total_cost > max_cost and self._can_reduce(leg_selections, spikes, locks):
            self._reduce_widest_leg(leg_selections, spikes, locks)
            total_cost = self._calculate_cost(leg_selections, row_price)

        #
        # Om det finns budget kvar efter kaosvarde-bredden,
        # anvand den till att bredda garderingen ytterligare.
        #
        total_cost = self._widen_to_use_budget(
            leg_selections, spikes, locks, max_cost, row_price, total_cost
        )

        self._print_system(
            leg_selections, total_cost, max_cost, row_price, coverage_strategy
        )

        return leg_selections, total_cost

    @staticmethod
    def _find_favorite(horses):
        #
        # Marknadens favorit i loppet - den lagst-oddsade hasten.
        # None om ingen hast i loppet har GILTIGA oddsdata.
        #
        # OBS: odds <= 0 racknas som ogiltig/saknad data, INTE som
        # ett riktigt, extremt lagt oddsvarde - riktiga decimalodds
        # ar alltid > 0 (i praktiken alltid > 1.0). ATG rapporterar
        # ibland 0.0 for hastar med i praktiken obefintligt
        # spelintresse (upptackt 2026-09-19, V85: tva hastar med
        # odds=0.0 i samma lopp) - utan detta filter skulle en
        # sadan korrupt nolla felaktigt utses till "favorit" bara
        # for att 0 ar numeriskt lagst, och tranga undan den
        # riktiga favoriten fran favoritskyddet helt.
        #
        with_odds = [h for h in horses if h.odds is not None and h.odds > 0]
        if not with_odds:
            return None
        return min(with_odds, key=lambda h: h.odds)

    @staticmethod
    def _find_top_two_by_odds(horses):
        #
        # De tva lagst-oddsade hastarna i loppet ("de tva
        # favoriterna") - anvands for LAS, samma princip som
        # _find_favorite men med tva hastar istallet for en.
        #
        # Om bara EN hast har giltiga oddsdata: den hasten
        # garanteras, och den andra platsen fylls av basta ovriga
        # hast efter Total Score (samma gracefulla nedgradering som
        # tidigare, bara for den ovanliga situationen dar faltet har
        # oddsdata for endast en hast).
        #
        # None om INGEN hast i loppet har giltiga oddsdata alls -
        # da faller anroparen tillbaka pa ren Total Score-ranking.
        #
        with_odds = sorted(
            (h for h in horses if h.odds is not None and h.odds > 0),
            key=lambda h: h.odds,
        )

        if len(with_odds) >= 2:
            return with_odds[:2]

        if len(with_odds) == 1:
            favorite = with_odds[0]
            #
            # Exkludera aven hastar med ogiltig odds (t.ex. en
            # struken hast som av nagon anledning anda nadde hit)
            # fran fyllnadsurvalet - annars kan samma problem som
            # for sjalva favoritdetekteringen smyga in har istallet.
            #
            ranked_horses = sorted(
                (h for h in horses if h.odds is None or h.odds > 0),
                key=lambda h: h.get_metric("total_score"),
                reverse=True,
            )
            others = [h for h in ranked_horses if h.number != favorite.number]
            return [favorite] + others[:1]

        return None

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

        #
        # OBS: odds <= 0 racknas som ogiltig/saknad data, samma
        # skal som i _find_favorite - annars kan en enda korrupt
        # nolla ("odds": 0.0) forstora hela favoritmarginalen for
        # ALLA hastar i loppet (margin blir 0, sa ingen riktig
        # favorit nagonsin kvalificerar sig som kontender).
        #
        with_odds = sorted(
            (h for h in horses if h.odds is not None and h.odds > 0),
            key=lambda h: h.odds,
        )
        without_odds = [h for h in horses if h.odds is None or h.odds <= 0]

        if with_odds:
            best_odds = with_odds[0].odds
            margin = best_odds * cls.FAVORITE_ODDS_MARGIN
            contenders = [h for h in with_odds if h.odds <= margin]
            rest_by_odds = [h for h in with_odds if h.odds > margin]
        else:
            contenders, rest_by_odds = [], []

        contender_numbers = {h.number for h in contenders}

        favorites = [
            h for h in ranked_by_score if h.number in contender_numbers
        ][:favorite_slots]

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

    def _widen_to_use_budget(self, leg_selections, spikes, locks, max_cost, row_price, total_cost):
        #
        # Anvander eventuellt kvarvarande budgetutrymme (efter att
        # kaosvarde-bredden och en ev. nedtrimning redan bestamts)
        # till att bredda garderingen ytterligare - annars kan en
        # generos budget lamnas till stor del outnyttjad.
        #
        # Breddar en hast i taget, alltid i det lopp (utanfor
        # spikar/las) med HOGST kaosvarde bland de som fortfarande
        # har utrymme kvar i faltet. Fortsatter tills nasta
        # breddning skulle sprangda budgeten, eller inget lopp
        # langre har plats kvar.
        #
        while True:
            candidates = [
                (index, leg)
                for index, leg in enumerate(leg_selections)
                if index >= spikes + locks
                and len(leg["horses"]) < len(leg["race"].horses)
            ]

            if not candidates:
                break

            _, widest_kaos_leg = max(
                candidates,
                key=lambda pair: getattr(pair[1]["race"], "kaosvarde", 0),
            )

            ranked_horses = sorted(
                widest_kaos_leg["race"].horses,
                key=lambda h: h.get_metric("total_score"),
                reverse=True,
            )
            chosen_numbers = {h.number for h in widest_kaos_leg["horses"]}
            next_horse = next(
                (h for h in ranked_horses if h.number not in chosen_numbers),
                None,
            )

            if next_horse is None:
                break

            widest_kaos_leg["horses"].append(next_horse)
            new_total_cost = self._calculate_cost(leg_selections, row_price)

            if new_total_cost > max_cost:
                widest_kaos_leg["horses"].pop()
                break

            total_cost = new_total_cost

        return total_cost

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
