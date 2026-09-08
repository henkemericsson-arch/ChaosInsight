from foundation.database_manager import get_default_manager

#
# Minsta antal giltiga historiska starter som kravs for att ge en
# baslinje overhuvudtaget. Under detta antal ar ett medelvarde for
# statistiskt opalitligt for att anvandas som utgangspunkt i en
# simulering - se samma forsiktighetsprincip som redan galler for
# Learning Engine:s inlarda kopplingsmultiplikatorer i
# 004_KAMT_v2_Monte_Carlo_Design.md.
#
MIN_STARTS_FOR_BASELINE = 3

#
# Minsta antal underliggande starter som kravs for att lita pa
# bana+distans-fallbacken (se track_distance_baseline_seconds).
# Hogre tröskel an MIN_STARTS_FOR_BASELINE eftersom detta ar ett
# betydligt grövre matt - hela faltets samlade prestation over tid
# blandas ihop, inte en enskild hasts egen formaga - och behover
# darfor mer data for att vara nagorlunda tillforlitligt.
#
MIN_STARTS_FOR_TRACK_DISTANCE_FALLBACK = 10


class BaselineCalculator:
    #
    # KAMT v2, Niva 1: rakner ut varje hasts absoluta
    # baskapacitet (sekunder per kilometer) fran dess EGEN
    # historik - inte ett generiskt falt-/rassnitt.
    #
    # Anvander samma underliggande data som den befintliga
    # tempo_differential() i foundation/database_manager.py, men
    # dar den raknar ut en DIFFERENTIAL mot faltets snitt, ger
    # BaselineCalculator ett ABSOLUT varde: hastens egen
    # genomsnittliga km-tid. Det ar det varde Niva 2:s
    # kopplingsmatriser sedan multiplicerar (se PDF-underlaget:
    # "Steg 1: Bestam hastens kapacitetsintervall (Basvarde)").
    #

    def __init__(self, db_manager=None):
        self.db = db_manager or get_default_manager()

    def horse_baseline_seconds(self, horse_name, target_distance=None, margin=100):
        #
        # Returnerar hastens genomsnittliga km-tid i sekunder,
        # over dess egna giltiga historiska starter (struken/
        # galopperad/diskad exkluderas redan av
        # DatabaseManager.horse_km_times). None om for lite
        # data finns for ett tillforlitligt varde.
        #
        times = self.db.horse_km_times(horse_name, target_distance, margin)

        if len(times) < MIN_STARTS_FOR_BASELINE:
            return None

        return round(sum(times) / len(times), 3)

    def horse_baseline_with_coverage(self, horse_name, target_distance=None, margin=100):
        #
        # Samma som horse_baseline_seconds, men returnerar aven
        # antalet starter baslinjen bygger pa - anvandbart for
        # att senare avgora hur mycket tillit en simulering ska
        # ge vardet (samma "data_coverage"-tanke som redan finns
        # i chaos_engine.py for KAMT v1).
        #
        times = self.db.horse_km_times(horse_name, target_distance, margin)

        if len(times) < MIN_STARTS_FOR_BASELINE:
            return None, len(times)

        return round(sum(times) / len(times), 3), len(times)

    def track_distance_baseline_seconds(self, track, distance, margin=100):
        #
        # Sista utvag-baslinje: banans/distansens genomsnittliga
        # km-tid over ALLA hastar (inte begransat till nagon
        # specifik hast) - anvands av RaceAnalyzer nar INGEN hast
        # i loppet har tillrackligt med egen historik, sa att
        # loppet inte behover hoppas over helt fran skuggsystemet.
        #
        # Kravs fler underliggande starter
        # (MIN_STARTS_FOR_TRACK_DISTANCE_FALLBACK) an for en
        # vanlig hastspecifik baslinje - se motivering vid
        # konstanten ovan.
        #
        average, n_starts = self.db.track_distance_average_km_time(
            track, distance, margin
        )

        if average is None or n_starts < MIN_STARTS_FOR_TRACK_DISTANCE_FALLBACK:
            return None

        return average
