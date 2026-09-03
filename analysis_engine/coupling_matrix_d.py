def _has_shoe(value):
    #
    # shod_front/shod_back kan komma som bade riktiga booleaner
    # och som text-/heltalsrepresentationer ("0"/"1", 0/1) beroende
    # pa lagringsvag - normalisera till en enda tolkning.
    #
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in ("", "0", "false", "False")
    return bool(value)


class EquipmentMatrix:
    #
    # KAMT v2, Niva 2, Matris D: Utrustning x Bana x Distans.
    #
    # VARNING: siffrorna nedan ar ett forsta utkast, granskade
    # tillsammans med anvandaren och en annan AI-assistent, men
    # fortfarande INTE verifierade mot verkliga utfall - se
    # 004_KAMT_v2_Monte_Carlo_Design.md for den fulla varningen.
    #
    # Producerar effekter som en fraktion (t.ex. -0.025 = -2,5 %)
    # att applicera pa hastens baskapacitet.
    #
    # Skoandring hanteras som en villkorlig trigger (inte ett fast
    # varde), eftersom samma handelse (en skoandring) kan betyda
    # motsatta saker beroende pa sammanhang. NAR triggern galler
    # flaggar den bara ett behov av korstabell-justering
    # ("forced_shoeing_change") - den rör ALDRIG Matris C:s
    # galopprisk direkt harifran. Den faktiska justeringen sker i
    # analysis_engine/cross_matrix_effects.py, enligt det
    # uttryckliga beslutet att matriserna inte far modifiera
    # varandra direkt.
    #

    def base_effect(self, track_condition, shod_front, shod_back, cart_type, distance):
        effect = 0.0
        barefoot = not _has_shoe(shod_front) and not _has_shoe(shod_back)

        if track_condition == "heavy":
            effect += -0.025 if barefoot else 0.005
        elif track_condition == "light" and barefoot:
            effect += 0.015

        if cart_type == "Amerikansk" and distance is not None:
            if distance <= 2000:
                effect += 0.010
            elif distance > 2600:
                effect += -0.005

        return round(effect, 4)

    def shoe_change_trigger(self, previous_shod_front, previous_shod_back,
                             current_shod_front, current_shod_back,
                             track_condition, precipitation_mm):
        #
        # Returnerar {"effect": float eller None, "flags": {...}}.
        # effect=None betyder "ingen trigger galler, anvand
        # base_effect() istallet". flags konsumeras av
        # cross_matrix_effects.py.
        #
        if previous_shod_front is None and previous_shod_back is None:
            #
            # Ingen tidigare start att jamfora mot - kan inte
            # avgora riktning, falla tillbaka pa base_effect.
            #
            return {"effect": None, "flags": {}}

        was_barefoot = not _has_shoe(previous_shod_front) and not _has_shoe(previous_shod_back)
        is_barefoot = not _has_shoe(current_shod_front) and not _has_shoe(current_shod_back)

        if was_barefoot == is_barefoot:
            #
            # Ingen riktningsandring skedde - base_effect racker.
            #
            return {"effect": None, "flags": {}}

        #
        # Regel 1 (Planerad lattning): Skor -> Barfota + Snabb bana
        #
        if not was_barefoot and is_barefoot and track_condition == "light":
            return {"effect": 0.015, "flags": {}}

        #
        # Regel 2 (Framtvingad skoning): Barfota -> Skor + Regn
        #
        if was_barefoot and not is_barefoot and (precipitation_mm or 0) > 0:
            return {"effect": 0.0, "flags": {"forced_shoeing_change": True}}

        return {"effect": None, "flags": {}}
