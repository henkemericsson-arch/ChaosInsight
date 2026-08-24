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
                "scratched": bool(start.get("out")),
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