class ResultParser:
    #
    # Tar emot rådata från races/{raceId}/extended (eller ett
    # enskilt lopp ur games-endpointens "races"-lista, som har
    # samma struktur) och bygger en enkel per-häst resultatlista,
    # för att jämföra mot systemets tidigare förslag.
    #
    # ATG anger ovanliga utfall (galopp, diskning, struken) via
    # egna explicita falt istallet for bara ett hogt finishOrder-
    # varde - de faltet plockas ut har direkt, sa att analys i
    # efterhand (Learning Engine, backfill) kan tolka utfallet
    # for vad det faktiskt ar, utan att gissa utifran finishOrder.
    #
    def parse(self, race_data):
        status = race_data.get("status")

        if status != "results":
            #
            # Loppet är inte avgjort än.
            #
            return None

        results = []

        for start in race_data.get("starts", []):
            result = start.get("result") or {}
            km_time = result.get("kmTime") or {}

            results.append({
                "number": start.get("number"),
                "name": start.get("horse", {}).get("name", ""),
                #
                # OBS: "scratched" ligger pa startens EGEN toppniva
                # (syskon till "result"), INTE i result-dictet, och
                # ar ett helt annat falt an "out" - "out" verkar
                # snarare betyda nagot i stil med "kom inte i mal/
                # galopperade/diskades", inte "struken". Bekraftat
                # mot verklig ATG-rådata (2026-09-06, V85 Jägersro):
                # en genuint struken hast hade "scratched": true och
                # SAKNADE "out" helt, medan en hast som galopperade
                # och diskades (men startade och sprang) hade
                # "out": true men "scratched" osatt. Att tidigare
                # lasa "out" har gett fel actual_scratched-varde i
                # hela historikdatabasen.
                #
                "scratched": bool(start.get("scratched")),
                "galloped": bool(result.get("galloped")),
                "disqualified": bool(result.get("disqualified")),
                "finish_order": result.get("finishOrder"),
                "place": result.get("place"),
                "final_odds": result.get("finalOdds"),
                "prize_money": result.get("prizeMoney"),
                "km_time": self._format_km_time(km_time),
                #
                # Rakod fran ATG nar det inte finns en riktig tid
                # (t.ex. "kub" vid galopp/diskning). None om en
                # riktig tid kunde tolkas istallet.
                #
                "km_time_status_code": km_time.get("code"),
            })

        return results

    @staticmethod
    def parse_scratchings_and_reserves(race_data, game_type):
        #
        # Extraherar strukningar och reservordning for loppet - pa
        # LOPP-niva, inte per hast. Anvands av Learning Engine for
        # att ratta hit/miss-berakningen nar en markerad hast blivit
        # struken och automatiskt ersatts av nasta tillgangliga
        # reserv enligt ATG:s regler.
        #
        # game_type: speltypen (t.ex. "V85") - reservordningen ligger
        # under just den speltypens egen pool i rådata
        # (race_data["pools"][game_type]["result"]["reserveOrder"]),
        # inte lopp-generellt, sa ratt speltyp maste anges.
        #
        # Returnerar (scratchings, reserve_order) - bada tomma
        # listor om nagot saknas, aldrig None (sa anropare slipper
        # None-kontroller).
        #
        scratchings = (race_data.get("result") or {}).get("scratchings") or []

        pool = (race_data.get("pools") or {}).get(game_type) or {}
        reserve_order = (pool.get("result") or {}).get("reserveOrder") or []

        return scratchings, reserve_order

    @staticmethod
    def _format_km_time(km_time):
        if not km_time:
            return None

        minutes = km_time.get("minutes")
        seconds = km_time.get("seconds")
        tenths = km_time.get("tenths")

        #
        # Om hasten galopperat/diskats innehaller kmTime bara
        # en kod (t.ex. "kub") istallet for en riktig tid.
        #
        if minutes is None or seconds is None or tenths is None:
            return None

        return f"{minutes}.{seconds:02d},{tenths}"
