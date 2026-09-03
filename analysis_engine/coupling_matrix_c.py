class IncidentRiskMatrix:
    #
    # KAMT v2, Niva 2, Matris C: Galopprisk x Spar x Bana.
    #
    # VARNING: siffrorna nedan ar ett forsta utkast, INTE
    # verifierade mot verkliga utfall - samma forsiktighet som
    # galler for Tabell D och Matris B.
    #
    # Producerar en RISKMULTIPLIKATOR att applicera pa hastens
    # egen historiska galoppfrekvens (fran
    # DatabaseManager.gallop_risk_score). Matrisen paverkas
    # ALDRIG direkt av andra matriser - korstabell-justeringar
    # (t.ex. fran Matris D:s skoandrings-trigger) hanteras separat
    # av analysis_engine/cross_matrix_effects.py, enligt det
    # uttryckliga beslutet att matriserna inte far modifiera
    # varandra direkt (se 004_KAMT_v2_Monte_Carlo_Design.md,
    # oppen fraga 5).
    #

    #
    # Extra risk per startposition, bara relevant vid voltestart
    # (rullande start bakom bil, i en kurva) - auto-start (fran
    # startbox, rakt fram) har inte samma sparrelaterade risk.
    # Position 9+ behandlas som position 8.
    #
    VOLTE_POSITION_RISK_MULTIPLIER = {
        1: 1.00, 2: 1.00, 3: 1.05,
        4: 1.15, 5: 1.15, 6: 1.25, 7: 1.25, 8: 1.35,
    }

    TRACK_CONDITION_RISK_MULTIPLIER = {
        "light": 1.00,
        "mediumheavy": 1.10,
        "heavy": 1.25,
        "winter": 1.20,
    }

    def risk_multiplier(self, start_position, start_method, track_condition):
        multiplier = 1.0

        if start_method == "volte" and start_position is not None:
            position = min(start_position, 8)
            multiplier *= self.VOLTE_POSITION_RISK_MULTIPLIER.get(position, 1.0)

        multiplier *= self.TRACK_CONDITION_RISK_MULTIPLIER.get(track_condition, 1.0)

        return round(multiplier, 4)
