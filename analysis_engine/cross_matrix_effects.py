class CrossMatrixEffects:
    #
    # KAMT v2, Niva 2: separat mekanism for korstabell-
    # interaktioner mellan matriserna A-D.
    #
    # Beslut (004_KAMT_v2_Monte_Carlo_Design.md, oppen fraga 5):
    # matriserna far INTE modifiera varandra direkt. Istallet
    # producerar respektive matris flaggor (se t.ex.
    # coupling_matrix_d.py:s shoe_change_trigger), och den har
    # mekanismen tolkar flaggorna och applicerar justeringar over
    # matrisgranserna - matriserna sjalva kanner aldrig till
    # varandra.
    #
    # VARNING: multiplikatorn nedan ar ovprovad, se samma
    # forsiktighet som galler for ovriga matrisvarden.
    #

    #
    # Regel 2 i Matris D (Framtvingad skoning i regn) flaggar
    # "forced_shoeing_change" - hasten springer med en balans den
    # inte ar van vid, vilket hojer galopprisken utover vad Matris
    # C:s egen berakning redan ger.
    #
    FORCED_SHOEING_GALLOP_RISK_MULTIPLIER = 1.15

    def apply(self, matrix_c_multiplier, matrix_d_flags):
        adjusted = matrix_c_multiplier

        if matrix_d_flags.get("forced_shoeing_change"):
            adjusted *= self.FORCED_SHOEING_GALLOP_RISK_MULTIPLIER

        return round(adjusted, 4)
