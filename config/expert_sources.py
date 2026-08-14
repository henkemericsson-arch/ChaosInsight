#
# Manuell koppling mellan ett spels game_id (samma id som
# visas i "Sammanfattning" och anvands som filnamn i
# data/races/) och de artikel-identifierare som behovs for
# att hamta experttips for just det spelet.
#
# Det finns inget palitligt satt att rakna ut dessa
# automatiskt - varje sajt namnger sina artiklar lite olika -
# sa de laggs till har for hand infor varje speldag man vill
# ha experttips for.
#
# travcash_slug: URL-sista-delen fran travcash.se
#   (t.ex. "v85-tips-lordag-aby-15-8")
# rekatochklart_url: hela artikel-URL:en fran
#   rekatochklart.com
#

EXPERT_SOURCES = {

    #
    # OBS: game_id nedan ar en gissning baserad pa monstret
    # fran tidigare spel (V85_ÅÅÅÅ-MM-DD_bana-id_speldag-id).
    # Kor "python main.py start" for Åby V85 2026-08-15 forst
    # och kontrollera det verkliga game_id som visas i
    # Sammanfattningen (samma som filnamnet i data/races/),
    # rata raden nedan om den inte stammer.
    #

    "V85_2026-08-15_5_2": {
        "travcash_slug": "v85-tips-lordag-aby-15-8",
        "rekatochklart_url": (
            "https://www.rekatochklart.com/trav/v85-tips/"
            "v85-tips-aby-15-8/"
        ),
    },

}
