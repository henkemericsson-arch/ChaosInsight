# ATG API configuration
# Base URLs and headers reverse-engineered from a captured HAR
# (www.atg.se browsing session, 2026-08-02).

# Game / race detail data (odds, starts, horses, drivers, trainers)
RACINGINFO_BASE_URL = "https://www.atg.se/services/racinginfo/v1/api"

# Calendar / day overview data (different host than racinginfo)
CALENDAR_BASE_URL = "https://horse-betting-info.prod.c1.atg.cloud/api-public/v0"

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "X-Brand": "ATG",
    "X-License": "SE",
    "X-Requested-By": "ATG",
}
