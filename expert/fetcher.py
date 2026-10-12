import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

#
# Hamtar webbsidor artigt: kollar robots.txt, vantar mellan anrop till
# samma sajt och talar om vem som fragar. Hamtar bara - tolkar ingenting
# (Bibelns Data Collector). Nat-anrop kan bytas ut i test via `session`.
#

USER_AGENT = "ChaosInsight/0.1 (privat analys; kontakt via anvandaren)"
MIN_SECONDS_BETWEEN_REQUESTS = 2.0
TIMEOUT = 30


class FetchBlocked(Exception):
    pass


class Fetcher:

    def __init__(self, session=None, sleep=time.sleep, now=time.monotonic):
        self.session = session or requests.Session()
        self._sleep = sleep
        self._now = now
        self._robots = {}
        self._last_request = {}

    def allowed(self, url):
        parts = urlparse(url)
        host = f"{parts.scheme}://{parts.netloc}"
        parser = self._robots.get(host)
        if parser is None:
            parser = urllib.robotparser.RobotFileParser()
            try:
                response = self.session.get(
                    host + "/robots.txt",
                    headers={"User-Agent": USER_AGENT},
                    timeout=TIMEOUT,
                )
                if response.status_code in (401, 403):
                    parser.disallow_all = True
                elif response.status_code >= 400:
                    parser.allow_all = True
                else:
                    parser.parse(response.text.splitlines())
            except requests.RequestException:
                # Kan inte avgora -> hamta inte.
                parser.disallow_all = True
            self._robots[host] = parser
        return parser.can_fetch(USER_AGENT, url)

    def _throttle(self, host):
        last = self._last_request.get(host)
        if last is not None:
            wait = MIN_SECONDS_BETWEEN_REQUESTS - (self._now() - last)
            if wait > 0:
                self._sleep(wait)
        self._last_request[host] = self._now()

    def get_text(self, url):
        if not self.allowed(url):
            raise FetchBlocked(f"robots.txt tillater inte hamtning av {url}")
        self._throttle(urlparse(url).netloc)
        response = self.session.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.text
