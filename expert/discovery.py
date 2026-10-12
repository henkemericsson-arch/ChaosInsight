import re
from datetime import date as _date
from urllib.parse import urljoin, urlparse

from expert.text import extract_links

#
# Hittar kallans artikel(ar) for ett visst spel: laser kallans
# oversiktssida for speltypen och valjer lankar vars text eller adress
# innehaller spelets datum. Ren funktion pa redan hamtad HTML - inget
# natverk.
#
# Datumformer som kanns igen: "10/10", "10-10", "10.10", "10 oktober",
# "10-oktober" samt (bara tillsammans med banans namn) sammanskrivet
# "1010" sist i adressen, som trav.se anvander ("...-jagersro-59").
# Bara lankar pa kallans egen sajt tas med (en artikel som lankar vidare
# till t.ex. atg.se ar inte en tipsartikel).
#

MONTHS = ["januari", "februari", "mars", "april", "maj", "juni", "juli",
          "augusti", "september", "oktober", "november", "december"]


def _fold(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower()
                  .replace("å", "a").replace("ä", "a").replace("ö", "o"))


def _host(url):
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _date_parts(game_date):
    year, month, day = (int(x) for x in str(game_date)[:10].split("-"))
    _date(year, month, day)   # validerar
    return day, month


def _matches_date(text, href, day, month, track_match):
    haystack = f"{text} {href}".lower()
    numeric = [f"{day}/{month}", f"{day}-{month}", f"{day}.{month}"]
    month_name = MONTHS[month - 1]
    named = [rf"{day}[\s\-]+{month_name}"]
    for token in numeric:
        if re.search(r"(?<!\d)" + re.escape(token) + r"(?!\d)", haystack):
            return True
    for pattern in named:
        if re.search(r"(?<!\d)" + pattern, haystack):
            return True
    if track_match:
        slug = urlparse(href).path.rstrip("/").rsplit("/", 1)[-1]
        if re.search(rf"(?<!\d){day}{month}$", slug):
            return True
    return False


def find_articles(index_html, index_url, game_date, track=None, limit=3, type_tokens=None):
    # type_tokens: ord som text/adress maste innehalla (t.ex. ("v85",)); None = inget krav.
    day, month = _date_parts(game_date)
    type_tokens = tuple(_fold(t) for t in (type_tokens or ()))
    track_key = _fold(track)
    found = []
    seen = set()
    for href, text in extract_links(index_html):
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        url = urljoin(index_url, href)
        if url in seen or _host(url) != _host(index_url):
            continue
        if urlparse(url).path.rstrip("/") == urlparse(index_url).path.rstrip("/"):
            continue
        if type_tokens and not any(t in _fold(f"{text} {href}") for t in type_tokens):
            continue
        track_match = bool(track_key) and track_key in _fold(f"{text} {href}")
        if not _matches_date(text, href, day, month, track_match):
            continue
        seen.add(url)
        found.append((2 if track_match else 1, url))
    found.sort(key=lambda item: -item[0])
    return [url for _, url in found[:limit]]
