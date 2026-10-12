#
# Återrullningsvakt (skyddsräcke 8, 005 avsnitt 18.3). Ren beslutsregel.
#
# `delta_ci` är intervallet för skillnaden i log-loss per lopp
# (aktiv version − förälder; positivt = den aktiva är sämre).
#

def decide(n_races, delta_ci, min_races):
    if n_races < min_races:
        return {"decision": "too_early",
                "reason": f"{n_races} lopp med aktuell version, kräver minst {min_races}"}
    if delta_ci is not None and delta_ci[0] > 0:
        return {"decision": "rollback",
                "reason": f"klart sämre än föregående: 95 % KI [{delta_ci[0]:+.4f}, {delta_ci[1]:+.4f}] över 0"}
    return {"decision": "keep", "reason": "inte klart sämre än föregående"}
