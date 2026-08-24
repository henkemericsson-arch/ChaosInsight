#
# Officiella radpriser fran ATG:s kundservice
# (atg-extern.kb.kundo.se/guide/
#  vilka-spelformer-finns-och-hur-hogt-ar-radpriset,
#  uppdaterad 2025-10-20).
#
# DD (Dagens Dubbel) har inget fast radpris - spelaren valjer
# sjalv insats (lagst 5 kr) som sedan multipliceras med
# antalet rader. Vi anvander lagsta insatsen (5 kr) som en
# approximation av "radpris" for att kunna rakna ut en
# jamforbar systemkostnad.
#

ROW_PRICES = {
    "V86": 0.25,
    "V85": 0.50,
    "V75": 0.50,
    "GS75": 1.00,
    "V65": 1.00,
    "V64": 1.00,
    "V5": 1.00,
    "V4": 2.00,
    "V3": 10.00,
    "DD": 5.00,
}

DEFAULT_ROW_PRICE = 1.00
