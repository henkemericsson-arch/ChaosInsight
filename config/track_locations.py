#
# Koordinater (lat, lon) för svenska trav- och galoppbanor,
# använda för att hämta väderprognos via SMHI:s öppna API.
#
# SMHI täcker bara Sverige. Utländska banor (t.ex. Enghien,
# Beverley, Charlottenlund i Danmark) finns inte med här, och
# WeatherClient hanterar det genom att helt enkelt inte hitta
# någon koordinat och hoppa över väderdata för det loppet.
#
# Koordinaterna är ungefärliga (bantätort), vilket räcker för
# SMHI:s prognosupplösning. Listan är ett första urval av de
# vanligaste banorna och bör kompletteras efter hand.
#

TRACK_LOCATIONS = {
    "Solvalla": (59.3573, 17.8267),
    "Åby": (57.6667, 12.0167),
    "Jägersro": (55.6203, 13.0508),
    "Bergsåker": (62.3908, 17.3069),
    "Färjestad": (59.3793, 13.5036),
    "Romme": (60.4858, 15.4181),
    "Åmål": (59.0517, 12.7011),
    "Axevalla": (58.3667, 13.4667),
    "Bollnäs": (61.3486, 16.3900),
    "Dannero": (58.4544, 14.8961),
    "Eskilstuna": (59.3708, 16.5097),
    "Gävle": (60.6749, 17.1413),
    "Halmstad": (56.6745, 12.8578),
    "Kalmar": (56.6634, 16.3567),
    "Karlshamn": (56.1697, 14.8628),
    "Lindesberg": (59.5936, 15.2358),
    "Mantorp": (58.2333, 15.3167),
    "Skellefteå": (64.7507, 20.9528),
    "Umåker": (63.8258, 20.2630),
    "Vaggeryd": (57.5000, 14.1333),
    "Visby": (57.6348, 18.2948),
    "Örebro": (59.2741, 15.2066),
    "Östersund": (63.1792, 14.6357),
    "Boden": (65.8252, 21.6887),
    "Arvika": (59.6550, 12.5892),
    "Tingsryd": (56.5289, 14.9797),
    "Rättvik": (60.8958, 15.1128),
    "Lycksele": (64.6011, 18.6802),
    "Solänget": (63.2891, 18.7159),
    "Bro Park": (59.5167, 17.6333),
}

#
# OBS: koordinaterna ovan för Rättvik, Lycksele, Solänget och
# Bro Park är preliminära uppskattningar och bör kontrolleras
# mot en karta innan de litas på skarpt.
#
