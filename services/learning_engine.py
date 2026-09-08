import json
import os
from datetime import datetime, timezone

from services.atg_client import ATGClient
from parsers.result_parser import ResultParser
from foundation.database_manager import DatabaseManager
from services.db import DB_PATH


class LearningEngine:
    #
    # Jämför ett tidigare sparat systemförslag
    # (från PredictionLogger) mot det faktiska
    # lopputfallet, rapporterar traffsakerhet, och skriver
    # en detaljerad observationspost per häst till den
    # vaxande historiktabellen "observations" i SQLite
    # (data/history/chaosinsight.db), via
    # foundation.database_manager.DatabaseManager.
    #
    # Historikdatan ar raw-material for framtida
    # mönsteranalys - t.ex. om en viss kusk eller häst
    # tenderar att over- eller undervarderas av crowden.
    # Sjalva mönsteranalysen byggs som ett separat, senare
    # steg, nar det finns tillräckligt med data att räkna på.
    #
    # Ingen automatisk viktjustering an - bara observation
    # och rapportering.
    #
    # Nar samtliga lopp i spelet ar avgjorda beräknas aven
    # den mojliga utdelningen. ATG:s spel (V64/V65/V75/V85/V86)
    # betalar ut pa flera nivaer (t.ex. 4, 5 och 6 ratt for V64),
    # med utdelning per niva i game_data["pools"][spel]["result"]
    # ["payouts"][niva] = {"systems": ..., "payout": ... (ore)}.
    #
    # Eftersom SystemGenerator bygger en fullstandig Cartesian-
    # tackning (alla kombinationer av valda hastar) racknas det
    # ut kombinatoriskt hur manga av vara egna rader som hamnar
    # pa varje ratt-niva - se _row_distribution().
    #
    # Reservsubstitution: om en markerad hast blir struken efter
    # att systemet sparats, ersatter ATG automatiskt markeringen
    # med nasta tillgangliga hast (som inte redan ar markerad) i
    # loppets reservordning
    # (race["pools"][spel]["result"]["reserveOrder"]). Hit/miss-
    # berakningen har tar hansyn till detta - annars skulle ett
    # lopp som egentligen traffade ratt (via reservbytet) felaktigt
    # visas som miss. Se _apply_reserve_substitution().
    #
    # OBS - viktig detalj upptackt vid felsokning: reservordningen
    # och strukningarna finns INTE i det per-lopp-anrop
    # (client.get_race_result(), som hamtar
    # /races/{race_id}/extended) som annars anvands for att hamta
    # sjalva resultatet (finishOrder, place, kmTime m.m.) - den
    # endpointen saknar "pools" helt. Bade scratchings och
    # reserveOrder finns bara i client.get_game(game_id) (hela
    # spelets endpoint). Darfor hamtas hela spelet EN GANG per
    # evaluate()-anrop (inte per lopp) for att fa fram den
    # informationen, medan sjalva resultatet fortfarande hamtas
    # per lopp som tidigare.
    #

    PREDICTIONS_DIR = "data/races"

    def __init__(self):
        self.client = ATGClient()
        self.result_parser = ResultParser()

    def evaluate(self, game_id):
        path = os.path.join(self.PREDICTIONS_DIR, f"{game_id}.json")

        if not os.path.exists(path):
            print(f"Ingen sparad prognos hittades for {game_id}.")
            return None

        with open(path, encoding="utf-8") as f:
            prediction = json.load(f)

        game_type = prediction.get("spel")
        #
        # OBS: parametern till evaluate() heter "game_id" men ar
        # egentligen prediction_id (filnamnet, inklusive strategi
        # och tidsstampel) - anvands har bara for att hitta filen.
        # Det RIKTIGA game_id:t (t.ex. "V85_2026-09-06_7_5") som
        # ATG:s API behover finns separat inuti den sparade filen.
        # Att av misstag skicka prediction_id till ATG:s API gav
        # "400 Bad Request" och gjorde att reservordningen aldrig
        # gick att hamta.
        #
        real_game_id = prediction.get("game_id")
        reserve_info_by_race_id = self._fetch_reserve_info(real_game_id, game_type)

        leg_reports = []

        for leg in prediction["legs"]:
            results = self._fetch_results(leg)
            scratchings, reserve_order = reserve_info_by_race_id.get(
                leg.get("race_id"), ([], [])
            )
            leg_report = self._build_leg_report(leg, results, scratchings, reserve_order)

            leg_reports.append(leg_report)

            #
            # Logga bara observationer för lopp som faktiskt
            # har en bekräftad vinnare - annars riskerar vi att
            # spara ofullständiga/felaktiga observationsrader.
            #
            if leg_report["status"] != "ej avgjort":
                self._log_observations(prediction, leg, results)

        undecided = [r for r in leg_reports if r["status"] == "ej avgjort"]
        decided = [r for r in leg_reports if r["status"] != "ej avgjort"]
        hits = [r for r in decided if r["hit"]]

        outcome = {
            "evaluated_legs": len(decided),
            "hits": len(hits),
            "undecided_legs": len(undecided),
            "legs": leg_reports,
        }

        payout = None
        if len(undecided) == 0:
            payout = self._calculate_payout(prediction, outcome)

        #
        # Spara varje utvardering i en historik istallet for att
        # bara skriva over det tidigare resultatet. ATG:s
        # resultatdata for redan avgjorda lopp kan i sallsynta
        # fall andras mellan tva hamtningar (t.ex. vid en
        # efterhandsrattning), och utan historik skulle en sadan
        # andring annars radera ett tidigare, korrekt resultat
        # utan mojlighet att aterstalla det.
        #
        history_entry = {
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "outcome": outcome,
            "payout": payout,
        }

        history = prediction.setdefault("evaluation_history", [])
        history.append(history_entry)

        prediction["outcome"] = outcome
        prediction["payout"] = payout

        with open(path, "w", encoding="utf-8") as f:
            json.dump(prediction, f, ensure_ascii=False, indent=2)

        self._print_report(prediction, outcome)
        return outcome

    def _fetch_reserve_info(self, game_id, game_type):
        #
        # Hamtar scratchings/reserveOrder for ALLA lopp i spelet
        # pa en gang, via get_game() (den enda endpointen som
        # faktiskt har "pools"-data). Returnerar
        # {race_id: (scratchings, reserve_order)}. Tom dict om
        # hamtningen misslyckas helt - ska aldrig stoppa resten
        # av utvarderingen, bara innebara att inget reservbyte
        # tillampas (samma som tidigare beteende).
        #
        if not game_type:
            return {}

        try:
            full_game_data = self.client.get_game(game_id)
        except Exception as exc:
            print(f"[Learning Engine] Kunde inte hamta reservordning: {exc}")
            return {}

        if not full_game_data:
            return {}

        reserve_info = {}
        for raw_race in full_game_data.get("races", []):
            race_id = raw_race.get("id")
            if race_id is None:
                continue
            scratchings, reserve_order = self.result_parser.parse_scratchings_and_reserves(
                raw_race, game_type
            )
            reserve_info[race_id] = (scratchings, reserve_order)

        return reserve_info

    def _fetch_results(self, leg):
        race_id = leg.get("race_id")
        if race_id is None:
            return None

        raw_data = self.client.get_race_result(race_id)

        if raw_data is None:
            return None

        return self.result_parser.parse(raw_data)

    @staticmethod
    def _apply_reserve_substitution(chosen_numbers, scratchings, reserve_order):
        #
        # Ersatter varje struken hast bland dina valda med nasta
        # tillgangliga reserv (som du inte redan har markerat, och
        # som inte heller sjalv ar struken), enligt ATG:s
        # reservordning for loppet. Om nagot av chosen_numbers inte
        # ar struket, lamnas det oforandrat.
        #
        # Exempel (bekraftat mot verklig ATG-data 2026-09-06):
        # chosen={2,7}, scratchings=[4,7],
        # reserve_order=[2,5,3,9,1,11,6,10,7,8,4]
        # -> hast 7 ar struken, 2 ar redan markerad -> nasta lediga
        # i turordningen ar 5 -> effektivt valda blir {2,5}.
        #
        if not scratchings or not reserve_order:
            return set(chosen_numbers)

        scratchings_set = set(scratchings)
        needs_replacement = [n for n in chosen_numbers if n in scratchings_set]

        if not needs_replacement:
            return set(chosen_numbers)

        effective = {n for n in chosen_numbers if n not in scratchings_set}

        for _ in needs_replacement:
            for candidate in reserve_order:
                if candidate in effective or candidate in scratchings_set:
                    continue
                effective.add(candidate)
                break

        return effective

    @staticmethod
    def _build_leg_report(leg, results, scratchings=None, reserve_order=None):
        if results is None:
            return {
                "race_number": leg["race_number"],
                "status": "ej avgjort",
                "hit": False,
            }

        winner = next(
            (r for r in results if r["finish_order"] == 1), None
        )

        if winner is None:
            #
            # ATG rapporterar ibland vinnaren via "place" istallet
            # for (eller utover) "finishOrder". Anvand place som
            # fallback nar finish_order inte racker.
            #
            winner = next(
                (r for r in results if r["place"] == 1), None
            )

        if winner is None:
            #
            # ATG kan sätta loppets status till "results" innan
            # alla placeringar (t.ex. efter fotofinish) är
            # fastställda. Utan en bekräftad vinnare (varken via
            # finish_order eller place) är loppet i praktiken
            # fortfarande oavgjort - räkna det inte som en miss.
            #
            return {
                "race_number": leg["race_number"],
                "status": "ej avgjort",
                "hit": False,
            }

        original_chosen = set(leg.get("chosen_numbers", []))
        effective_chosen = LearningEngine._apply_reserve_substitution(
            original_chosen, scratchings or [], reserve_order or []
        )

        hit = winner["number"] in effective_chosen

        report = {
            "race_number": leg["race_number"],
            "status": "avgjort",
            "winner_number": winner["number"],
            "winner_name": winner["name"],
            "chosen_numbers": sorted(original_chosen),
            "hit": hit,
        }

        if effective_chosen != original_chosen:
            #
            # En eller flera av dina ursprungligen valda hastar
            # blev strukna och ersattes automatiskt av ATG:s
            # reservordning - synliggor det i rapporten istallet
            # for att bara tyst byta ut hit/miss-vardet.
            #
            report["effective_chosen_numbers"] = sorted(effective_chosen)
            report["reserve_substitution_applied"] = True

        return report

    @staticmethod
    def _row_distribution(leg_counts, leg_hits):
        #
        # Rackar ut, for en fullstandig Cartesian-tackning, hur
        # manga rader som hamnar pa exakt J ratt, for varje J.
        #
        # For ett lopp vi missade helt (vinnaren fanns inte bland
        # vara hastar) bidrar loppet alltid med 0 ratt, oavsett
        # vilken av vara hastar raden rakar ha i det loppet - sa
        # de loppen paverkar bara hur manga rader som "delar" pa
        # varje utfall (en multiplikator), inte sjalva ratt-antalet.
        #
        # For ett lopp vi traffade i kan varje rad antingen ha
        # vinnaren (1 mojlighet, +1 ratt) eller nagon av vara
        # ovriga hastar (count-1 mojligheter, +0 ratt).
        #
        # poly[j] efter konvolution = antal rader med exakt j
        # ratt bland de traffade loppen (vilket ar samma som det
        # totala antalet ratt, eftersom missade lopp aldrig ger
        # ratt).
        #
        miss_multiplier = 1
        hit_leg_counts = []

        for count, hit in zip(leg_counts, leg_hits):
            if hit:
                hit_leg_counts.append(count)
            else:
                miss_multiplier *= count

        poly = [1]
        for count in hit_leg_counts:
            new_poly = [0] * (len(poly) + 1)
            for j, ways in enumerate(poly):
                #
                # Valde vinnaren i detta lopp -> ett ratt mer.
                #
                new_poly[j + 1] += ways * 1
                #
                # Valde nagon av de ovriga hastarna -> inget
                # extra ratt.
                #
                if count > 1:
                    new_poly[j] += ways * (count - 1)
            poly = new_poly

        return [ways * miss_multiplier for ways in poly]

    def _calculate_payout(self, prediction, outcome):
        game_type = prediction.get("spel")
        game_id = prediction.get("game_id")

        if not game_type or not game_id:
            return None

        try:
            game_data = self.client.get_game(game_id)
        except Exception as exc:
            print(f"[Learning Engine] Kunde inte hamta utdelning: {exc}")
            return None

        if not game_data:
            return None

        pool = (game_data.get("pools") or {}).get(game_type)
        if not pool:
            print(
                f"[Learning Engine] Ingen poolinformation for {game_type} "
                f"hittades - kan inte rakna ut utdelning."
            )
            return None

        payouts_by_level = ((pool.get("result") or {}).get("payouts")) or {}

        if not payouts_by_level:
            print(
                f"[Learning Engine] Ingen utdelningsdata hittades an "
                f"for {game_type} - kan inte rakna ut utdelning."
            )
            return None

        #
        # Bygg upp leg_counts/leg_hits i samma ordning for bade
        # antal valda hastar och traff/miss per lopp. leg_hits
        # anvander redan den reservsubstitution-korrigerade
        # hit-flaggan fran outcome["legs"] (se _build_leg_report).
        #
        hits_by_race_number = {
            leg_report["race_number"]: leg_report["hit"]
            for leg_report in outcome["legs"]
        }

        leg_counts = []
        leg_hits = []

        for leg in prediction["legs"]:
            race_number = leg["race_number"]
            leg_counts.append(len(leg.get("chosen_numbers", [])) or 1)
            leg_hits.append(hits_by_race_number.get(race_number, False))

        distribution = self._row_distribution(leg_counts, leg_hits)

        breakdown = []
        total_payout = 0.0

        for level_str, info in payouts_by_level.items():
            try:
                level = int(level_str)
            except (TypeError, ValueError):
                continue

            rows = distribution[level] if level < len(distribution) else 0
            if rows <= 0:
                continue

            per_row_kr = info.get("payout", 0) / 100
            subtotal = rows * per_row_kr
            total_payout += subtotal

            breakdown.append({
                "level": level,
                "rows": rows,
                "per_row": round(per_row_kr, 2),
                "subtotal": round(subtotal, 2),
            })

        breakdown.sort(key=lambda b: b["level"], reverse=True)

        total_cost = prediction.get("total_cost", 0)

        return {
            "breakdown": breakdown,
            "total_payout": round(total_payout, 2),
            "net": round(total_payout - total_cost, 2),
        }

    def _log_observations(self, prediction, leg, results):
        results_by_number = {r["number"]: r for r in results}

        logged_at = datetime.now(timezone.utc).isoformat()

        db = DatabaseManager()

        #
        # Rensa bort eventuella tidigare observationer for exakt
        # denna (game_id, strategi, lopp) innan nya skrivs - annars
        # kan gamla, ev. felaktiga rader (t.ex. fran innan en
        # bugfix) bli kvar sida vid sida med de nya, korrekta.
        # Gors vid VARJE (om-)utvardering, inte bara vid en
        # engangsstadning - sa databasen forblir ren aven vid
        # framtida omvarderingar.
        #
        deleted = db.delete_observations_for_leg(
            prediction["game_id"], prediction.get("strategy"), leg.get("race_id")
        )
        if deleted:
            print(
                f"[Learning Engine] Rensade {deleted} gamla observationer "
                f"for V{leg['race_number']} fore omvardering"
            )

        for horse in leg["horses"]:
            result = results_by_number.get(horse["number"], {})

            observation = {
                "logged_at": logged_at,
                "game_id": prediction["game_id"],
                "strategy": prediction.get("strategy"),
                "race_id": leg.get("race_id"),
                "date": prediction["date"],
                "track": leg["track"],
                "distance": leg.get("distance"),
                "start_method": leg.get("start_method"),
                "track_condition": leg.get("track_condition"),
                "kaosvarde": leg.get("kaosvarde"),
                "weather": prediction.get("weather"),

                "horse_number": horse["number"],
                "horse_name": horse["name"],
                "driver": horse.get("driver"),
                "trainer": horse.get("trainer"),
                "start_position": horse.get("start_position"),
                "odds": horse.get("odds"),
                "bet_percentage": horse.get("bet_percentage"),
                "shod_front": horse.get("shod_front"),
                "shod_back": horse.get("shod_back"),
                "shoe_changed": horse.get("shoe_changed"),
                "sulky_changed": horse.get("sulky_changed"),
                "cart_type": horse.get("cart_type"),
                "career_earnings": horse.get("career_earnings"),
                "driver_win_pct": horse.get("driver_win_pct"),
                "trainer_win_pct": horse.get("trainer_win_pct"),
                "horse_win_pct": horse.get("horse_win_pct"),

                "predicted_total_score": horse.get("total_score"),
                "predicted_crowd_index": horse.get("crowd_index"),
                "predicted_chaos_index": horse.get("chaos_index"),
                "predicted_expert_index": horse.get("expert_index"),
                "chosen_by_system": horse.get("chosen"),

                "actual_finish_order": result.get("finish_order"),
                "actual_place": result.get("place"),
                "actual_final_odds": result.get("final_odds"),
                "actual_scratched": result.get("scratched"),
                "actual_galloped": result.get("galloped"),
                "actual_disqualified": result.get("disqualified"),
                "actual_prize_money": result.get("prize_money"),
                "actual_km_time": result.get("km_time"),
                "actual_km_time_status_code": result.get("km_time_status_code"),
            }

            #
            # or_ignore=True skyddar bara mot en ren omkorning av
            # exakt samma logged_at/game_id/race_id/horse_number -
            # om samma lopp utvarderas pa nytt senare (t.ex. via
            # "Tvinga omvardering") far det en ny logged_at-
            # tidsstampel och loggas som en ny, egen observation,
            # precis som tidigare.
            #
            db.insert_observation(observation, or_ignore=True)

        db.commit()
        db.close()

        print(
            f"[Learning Engine] Loggade {len(leg['horses'])} observationer "
            f"for V{leg['race_number']} till {DB_PATH}"
        )

    @staticmethod
    def _print_report(prediction, outcome):
        print()
        print("=" * 60)
        print("Learning Engine - utvardering")
        print("=" * 60)

        spel = prediction["spel"]
        track = prediction["track"]
        date = prediction["date"]

        print(f"Spel: {spel} | Bana: {track} | Datum: {date}")
        print()

        for leg in outcome["legs"]:
            race_number = leg["race_number"]

            if leg["status"] == "ej avgjort":
                print(f"V{race_number}: ej avgjort an")
                continue

            marker = "TRAFF" if leg["hit"] else "miss "
            winner_number = leg["winner_number"]
            winner_name = leg["winner_name"]
            chosen_numbers = leg["chosen_numbers"]

            substitution_note = ""
            if leg.get("reserve_substitution_applied"):
                substitution_note = (
                    f"  [REERVBYTE: {chosen_numbers} -> "
                    f"{leg['effective_chosen_numbers']}]"
                )

            print(
                f"V{race_number}: {marker}  "
                f"vinnare: {winner_number}. {winner_name}  "
                f"| dina hastar: {chosen_numbers}"
                f"{substitution_note}"
            )

        print()

        evaluated_legs = outcome["evaluated_legs"]
        hits = outcome["hits"]
        undecided_legs = outcome["undecided_legs"]

        if evaluated_legs > 0:
            hit_rate = round(100 * hits / evaluated_legs, 1)
            print(
                f"Traffsakerhet: {hits}/{evaluated_legs} "
                f"avgjorda lopp ({hit_rate} %)"
            )

        if undecided_legs > 0:
            print(f"{undecided_legs} lopp ar annu inte avgjorda.")

        payout = prediction.get("payout")
        if payout is not None:
            print()
            if payout["breakdown"]:
                for entry in payout["breakdown"]:
                    print(
                        f"{entry['level']} ratt: {entry['rows']} rad(er) x "
                        f"{entry['per_row']} kr = {entry['subtotal']} kr"
                    )
                print(f"Total utdelning: {payout['total_payout']} kr")
            else:
                print("Ingen utdelning denna gang.")
            print(f"Netto: {payout['net']} kr")
