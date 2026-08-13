class ResultParser:

    #
    # Tar emot rådata från races/{raceId}/extended och bygger
    # en enkel per-häst resultatlista, för att jämföra mot
    # systemets tidigare förslag.
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

            results.append({
                "number": start.get("number"),
                "name": start.get("horse", {}).get("name", ""),
                "finish_order": result.get("finishOrder"),
                "place": result.get("place"),
                "final_odds": result.get("finalOdds"),
            })

        return results
