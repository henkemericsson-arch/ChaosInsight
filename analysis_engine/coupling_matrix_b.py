class TrackWeatherMatrix:
    #
    # KAMT v2, Niva 2, Matris B: Distans x Bana x Vader.
    #
    # VARNING: siffrorna nedan ar ett forsta utkast, INTE
    # verifierade mot verkliga utfall - samma forsiktighet som
    # galler for Tabell D i 004_KAMT_v2_Monte_Carlo_Design.md.
    # Formeln (istallet for en uppslagstabell) valdes eftersom
    # kombinationsutrymmet (distans x bantyp x nederbordsniva) ar
    # for stort for att racka upp for hand - men de faktiska
    # koefficienterna behover granskas mot verklig travkunskap
    # innan de anvands skarpt, och ska sa smaningom justeras av
    # Learning Engine, med samma tröskel-fallback-princip
    # (MIN_STARTS_FOR_BASELINE-monstret) som redan galler for
    # ovriga inlarda varden.
    #
    # Effekten returneras som en fraktion att applicera pa
    # hastens baskapacitet, t.ex. -0.015 = -1,5 %.
    #

    #
    # Hur mycket varje bantyp forstarker eller dampar effekten
    # per 1000 m avvikelse fran referensdistansen. Lätt bana
    # gynnar nagot mer ju langre loppet ar (uthallighet lonar sig
    # utan negativa underlagseffekter); tunga banor straffar
    # hardare ju langre loppet blir (fysiskt slitsammare over tid).
    #
    TRACK_DISTANCE_SENSITIVITY = {
        "light": 0.003,
        "mediumheavy": -0.005,
        "heavy": -0.015,
        "winter": -0.010,
    }

    REFERENCE_DISTANCE_M = 2140

    #
    # Ytterligare straff per mm nederbord, utover bantypens redan
    # rapporterade tillstand (ATG:s egen track_condition ar redan
    # den huvudsakliga signalen - nederbord lagger till en extra,
    # mer aktuell justering ovanpa den).
    #
    RAIN_PENALTY_PER_MM = -0.003

    #
    # Tak sa extremvader inte ger orimligt stora effekter.
    #
    MAX_RAIN_PENALTY = -0.03

    def effect(self, distance, track_condition, precipitation_mm=0):
        if distance is None or track_condition is None:
            return 0.0

        sensitivity = self.TRACK_DISTANCE_SENSITIVITY.get(track_condition, 0.0)
        distance_diff_thousands = (distance - self.REFERENCE_DISTANCE_M) / 1000
        distance_effect = sensitivity * distance_diff_thousands

        rain_effect = self.RAIN_PENALTY_PER_MM * (precipitation_mm or 0)
        rain_effect = max(rain_effect, self.MAX_RAIN_PENALTY)

        return round(distance_effect + rain_effect, 4)
