#
# Expertkallor. Lagg till en kalla genom att lagga till en post i
# SOURCES - ingen kodandring behovs. Tolkningen ar gemensam for alla
# kallor (expert/interpreter.py).
#
# name        - kallans namn (sparas i expert_tips.source)
# enabled     - False = hoppas over
# weight      - kallans vikt i expert_index (1.0 = normal)
# index_urls  - speltyp -> oversiktssida dar kallan listar sina artiklar
#
# OBS: index_urls ar tagna fran sajternas startsidor och inte provade mot
# riktiga artiklar annu (travcash och rekatochklart ar kontrollerade mest).
# Hamtning respekterar robots.txt (expert/fetcher.py). Kallor som inte
# tillater automatisk hamtning hoppas over av sig sjalva.
#

SOURCES = [
    {
        "name": "travcash",
        "enabled": True,
        "weight": 1.0,
        "index_urls": {
            "V85": "https://travcash.se/v85-tips/",
            "V86": "https://travcash.se/v86-tips/",
            "GS75": "https://travcash.se/gs75-tips/",
            "V64": "https://travcash.se/v64-tips/",
            "V65": "https://travcash.se/v65-tips/",
        },
    },
    {
        "name": "rekatochklart",
        "enabled": True,
        "weight": 1.0,
        "index_urls": {
            "V85": "https://www.rekatochklart.com/trav/v85-tips/",
            "V86": "https://www.rekatochklart.com/trav/v86-tips/",
            "V64": "https://www.rekatochklart.com/trav/v64-tips/",
        },
    },
    {
        "name": "trav.se",
        "enabled": True,
        "weight": 1.0,
        "index_urls": {
            "V85": "https://www.trav.se/speltips/speltyp/v85",
            "V86": "https://www.trav.se/speltips/speltyp/v86",
            "GS75": "https://www.trav.se/speltips/speltyp/grand-slam-75",
        },
    },
    {
        "name": "travstugan",
        "enabled": True,
        "weight": 1.0,
        "index_urls": {
            "V85": "https://www.travstugan.se/v85",
            "V86": "https://www.travstugan.se/v86",
            "GS75": "https://www.travstugan.se/gs75",
        },
    },
    {
        "name": "svenskatrav",
        "enabled": True,
        "weight": 1.0,
        "index_urls": {},   # sidstruktur ej kartlagd annu
    },
    {
        "name": "guiden",
        "enabled": False,   # ev. betalvagg - kontrollera innan aktivering
        "weight": 1.0,
        "index_urls": {},
    },
    {
        "name": "atg",
        "enabled": False,   # mest nyheter, svag expertsignal
        "weight": 1.0,
        "index_urls": {},
    },
    {
        "name": "trav.tips",
        "enabled": False,
        "weight": 1.0,
        "index_urls": {},
    },
    # minadel.se utelamnad: robots.txt avvisade hamtning vid forsta forsoket.
]

#
# Manuell reservlankning: {game_id: {kalla: artikel-url}} - anvands om
# automatisk artikelhittning inte ger traff for en kalla.
#
MANUAL_ARTICLES = {
    "V85_2026-08-15_6_5": {
        "rekatochklart": "https://www.rekatochklart.com/trav/v85-tips/v85-tips-aby-15-8/",
    },
}

#
# False = indexet beraknas och loggas (metric "expert_index_obs") men
# paverkar inte Total Score. True = metric "expert_index" som CrowdEngine
# raknar in. Aktiveras forst nar Learning Engine visat att det tillfor nagot.
#
EXPERT_INDEX_ACTIVE = False
