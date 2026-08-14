import re

from providers.base_provider import BaseProvider


class RekatochklartProvider(BaseProvider):

    #
    # Samlar in tips fran rekatochklart.com. Sidan har ingen
    # egen API, sa vi laser den publicerade artikelns HTML
    # och tolkar vilka hastnummer som ar markerade som
    # rekommenderade (CSS-klassen "bg-warning" pa varje
    # hastnummers badge).
    #
    # Returnerar ren fakta: {loppnamn: [hastnummer, ...]}.
    # Ingen tolkning av vad det betyder gors har - det gor en
    # framtida ExpertAnalyzer.
    #

    name = "Rekatochklart"

    LEG_PATTERN = re.compile(
        r'class="badge[^"]*\bv85\b[^"]*">(V\d+-\d+)<'
    )

    BADGE_PATTERN = re.compile(
        r'class="badge( bg-warning)?">(\d+)<'
    )

    def __init__(self):

        from services.http_client import HttpClient

        self.http = HttpClient()

    def collect(self, url):

        html = self.http.get_text(url=url, headers={})

        return self._parse_tips(html)

    def _parse_tips(self, html):

        #
        # Sidan bygger varje lopp som ett eget block. Vi
        # delar upp texten vid varje loppetikett (t.ex.
        # "V85-1") och letar sedan efter markerade
        # hastnummer inom det blocket, fram till nasta
        # loppetikett.
        #

        leg_matches = list(self.LEG_PATTERN.finditer(html))

        tips = {}

        for index, match in enumerate(leg_matches):

            leg_name = match.group(1)

            block_start = match.end()

            block_end = (
                leg_matches[index + 1].start()
                if index + 1 < len(leg_matches)
                else block_start + 3000
            )

            block = html[block_start:block_end]

            tipped_numbers = [
                int(number)
                for is_tipped, number in self.BADGE_PATTERN.findall(block)
                if is_tipped
            ]

            tips[leg_name] = tipped_numbers

        return tips
