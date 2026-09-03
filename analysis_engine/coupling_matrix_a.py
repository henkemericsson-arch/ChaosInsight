class PositionMatrix:
    #
    # KAMT v2, Niva 2, Matris A: Startspar x Kuskform x Tempo.
    #
    # VARNING: koefficienterna nedan ar ett forsta utkast, INTE
    # verifierade mot verkliga utfall - samma forsiktighet som
    # galler for matriserna B, C och D.
    #
    # OBS: vi har ingen egen datapunkt for "offensiv kuskstil" -
    # anvander kuskens vinstprocent (driver_win_pct) som en
    # rimlig, men ofullstandig, stallforetradare for det.
    #
    # Producerar inte en enkel effekt-siffra som B/C/D, utan en
    # "spetschans"-vikt som anvands av den travspecifika
    # simuleringen (TravRaceSimulator) for att avgora vem som
    # tar ledningen i en given simulering - se
    # LEAD_BONUS/DOOM_PENALTY nedan for kapacitetseffekterna
    # nar startkampen ar avgjord.
    #

    #
    # Antaganden vid saknad data.
    #
    DEFAULT_START_POSITION = 8
    DEFAULT_DRIVER_WIN_PCT = 15.0

    #
    # Kapacitetseffekter (samma fraktions-konvention som B/C/D:
    # positivt = snabbare/battre) beroende pa utfallet i
    # startkampen.
    #
    LEAD_BONUS = 0.010
    DOOM_PENALTY = -0.015

    def spets_score(self, start_position, driver_win_pct, start_method):
        position = (
            start_position if start_position is not None
            else self.DEFAULT_START_POSITION
        )
        #
        # Lagre spar-nummer -> hogre chans att ta ledningen.
        # Golvas vid 0.1 sa aven ett mycket dåligt spar har en
        # liten (inte noll) chans i en given simulering.
        #
        position_score = max(0.1, 1.0 - (position - 1) * 0.08)

        win_pct = (
            driver_win_pct if driver_win_pct is not None
            else self.DEFAULT_DRIVER_WIN_PCT
        )
        driver_score = win_pct / 100

        #
        # Auto-start (raka spar fran startbox) ar mer
        # positionsstyrt; voltestart (rullande start i kurva)
        # ger kusken mer utrymme att pavaraka utfallet.
        #
        if start_method == "auto":
            weight = position_score * 0.7 + driver_score * 0.3
        else:
            weight = position_score * 0.5 + driver_score * 0.5

        return round(weight, 4)
