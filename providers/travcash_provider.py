import re

from providers.base_provider import BaseProvider


class TravcashProvider(BaseProvider):

    #
    # Samlar in tips fran travcash.se via deras WordPress-
    # API (wp-json), som ger strukturerad JSON istallet for
    # att behova skrapa hela sidans HTML. Sjalva tipsen ligger
    # dock som HTML-tabellrader inuti content.rendered-faltet,
    # sa vi tolkar den delen.
    #
    # Returnerar ren fakta: {loppnamn: [hastnummer, ...]}.
    # Ingen tolkning av vad det betyder gors har - det gor en
    # framtida ExpertAnalyzer.
    #

    name = "Travcash"

    BASE_URL = "https://travcash.se/wp-json/wp/v2/posts"

    LEG_LABEL_PATTERN = re.compile(r'^V\d+-\d+$')

    CELL_PATTERN = re.compile(r'<div>([^<]+)</div>')

    def __init__(self):

        from services.http_client import HttpClient

        self.http = HttpClient()

    def collect(self, slug):

        posts = self.http.get(
            url=self.BASE_URL,
            headers={},
            params={"slug": slug},
        )

        if not posts:
            return {}

        html = posts[0].get("content", {}).get("rendered", "")

        return self._parse_tips(html)

    def _parse_tips(self, html):

        row_chunks = html.split('info-table__row')[1:]

        tips = {}

        for chunk in row_chunks:

            #
            # Varje rad har tva enkla textceller. Ordningen
            # (tips forst eller etikett forst) verkar variera,
            # sa vi identifierar etiketten via monster (t.ex.
            # "V85-3") istallet for att lita pa positionen.
            #

            cells = self.CELL_PATTERN.findall(chunk)[:2]

            if len(cells) < 2:
                continue

            leg_name = next(
                (c for c in cells if self.LEG_LABEL_PATTERN.match(c.strip())),
                None,
            )

            if leg_name is None:

                #
                # Rubrikrad (t.ex. "Avd" / "Hastar"),
                # ingen loppdata - hoppa over.
                #

                continue

            value_text = next(c for c in cells if c != leg_name)

            tips[leg_name] = self._extract_numbers(value_text)

        return tips

    @staticmethod
    def _extract_numbers(text):

        #
        # Hanterar bade "4,6,7" och "9 Zucchini C.D."
        # (ett enda spikat hastnummer foljt av namn).
        #

        numbers = re.findall(r'\d+', text)

        if ',' in text:
            return [int(n) for n in numbers]

        if numbers:
            return [int(numbers[0])]

        return []
