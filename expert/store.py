#
# Bygger "senaste tillgangliga tips" ur lagrade rader. Ren logik, inget
# SQL (databasen nas bara via DatabaseManager).
#
from expert.tip import ExpertTip


def latest_per_source(rows):
    # Per kalla anvands bara den senaste hamtningen (fetched_at) - en ny
    # hamtning ersatter den gamla, aldrig en blandning av bada.
    latest = {}
    for row in rows:
        source = row["source"]
        if source not in latest or row["fetched_at"] > latest[source]:
            latest[source] = row["fetched_at"]
    tips = []
    for row in rows:
        if row["fetched_at"] == latest[row["source"]]:
            tips.append(ExpertTip(
                source=row["source"], leg=row["leg"], horse_number=row["horse_number"],
                signal=row["signal"], horse_name=row.get("horse_name"),
                rank=row.get("rank"), rank_of=row.get("rank_of"),
                confidence=row.get("confidence") or 1.0,
            ))
    return tips
