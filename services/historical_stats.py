import threading

from foundation.database_manager import DatabaseManager, get_default_manager


class HistoricalStatsProvider:
    #
    # Tunn kompatibilitetsyta ovanpa foundation.database_manager.
    # Historisk statistik-logiken (distance_score,
    # track_condition_score, gallop_risk_score, tempo_differential)
    # bor numera i DatabaseManager, enligt Bibelns grundprincip 3
    # ("Ingen modul far lasa filer direkt. All filhantering gar via
    # respektive manager.") - den har filen kande tidigare till
    # databasschemat direkt via egna SQL-fragor, vilket den inte
    # langre gor.
    #
    # Behalls som ett tunt skal sa att befintliga anropare (t.ex.
    # analysis/chaos_engine.py) inte behover andras - de kan bytas
    # till att anvanda DatabaseManager direkt i ett senare
    # migreringssteg, i enlighet med 003_Restructuring_Plan.md:s
    # stegvisa migreringsordning.
    #

    def __init__(self, db_path=None):
        self._manager = DatabaseManager(db_path) if db_path else get_default_manager()

    def distance_score(self, horse_name, target_distance, margin=100):
        return self._manager.distance_score(horse_name, target_distance, margin)

    def track_condition_score(self, horse_name, target_condition):
        return self._manager.track_condition_score(horse_name, target_condition)

    def gallop_risk_score(self, horse_name):
        return self._manager.gallop_risk_score(horse_name)

    def tempo_differential(self, horse_name, target_distance, margin=100):
        return self._manager.tempo_differential(horse_name, target_distance, margin)


#
# Tradlokal cache (INTE en global processomfattande singleton) -
# samma princip och samma anledning som i
# foundation/database_manager.py:s get_default_manager().
#
# Den har filen hade tidigare EN EGEN global singleton
# (_default_provider = None, delad av alla tradar) som cachade
# hela HistoricalStatsProvider-objektet - INKLUSIVE dess
# self._manager, vars SQLite-anslutning skapades i vilken trad som
# forst rakade anropa get_default_provider(). Det gjorde att
# database_manager.py:s threading.local()-fix kringgicks helt
# harifran: chaos_engine.py haller sin egen referens till
# get_default_provider()-resultatet, sa aven om DatabaseManager
# sjalv blivit tradsaker, forblev HistoricalStatsProvider-skalet
# ovanfor det delat mellan tradar - vilket orsakade exakt samma
# "SQLite objects created in a thread can only be used in that
# same thread"-krasch en trad senare (t.ex. nasta dags forfragan
# efter att bakgrundstraden for automatisk backfill eller
# Werkzeugs egna tradhantering skapat en ny trad).
#
_thread_local = threading.local()


def get_default_provider():
    if getattr(_thread_local, "provider", None) is None:
        _thread_local.provider = HistoricalStatsProvider()
    return _thread_local.provider
