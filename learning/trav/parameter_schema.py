#
# Travspecifika parametrar och deras baseline-värden (adapter-lagret).
# Den generella koden i learning/tuning/ känner inte till något härifrån.
#
# Baseline = de värden som tidigare låg som klasskonstanter i
# CrowdEngine, ChaosEngine och ScoreEngine. Ändras de här ändras
# utgångspunkten för nya databaser; en befintlig baseline (version 0) i
# databasen rörs aldrig.
#
# Namnen har formen "grupp.namn". Gruppen är den modul som läser dem.
#

BASELINE = {
    # CrowdEngine - Crowd Index (av spelets 100 %: 20 + 10 + 10 + 5)
    "crowd.odds": 20,
    "crowd.streck": 10,
    "crowd.trend": 10,
    "crowd.expert": 5,

    # ChaosEngine - Kaos Index
    "chaos.start_position": 8,
    "chaos.driver_form": 8,
    "chaos.horse_form": 10,
    "chaos.trainer_form": 5,
    "chaos.distance": 5,
    "chaos.track_condition": 4,
    "chaos.gallop_risk": 5,
    "chaos.tempo": 5,

    # ScoreEngine - Total Score = crowd * CI + chaos * KI
    "score.crowd": 0.50,
    "score.chaos": 0.50,
}
