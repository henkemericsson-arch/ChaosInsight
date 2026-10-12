from html.parser import HTMLParser

#
# HTML -> rader av ren text. Enda uppgiften: ge tolkaren en lista med
# rader i lasordning, utan script/meny/sidfot. Tolkar ingenting.
#
# Blockelement (p, div, h1.., li, br ...) ger ny rad. Celler i en
# tabellrad (tr) slas ihop till en rad med " | " mellan cellerna.
#

SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "aside", "form", "head"}
BREAK_TAGS = {
    "p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
    "tr", "table", "section", "article", "header", "blockquote",
}
CELL_TAGS = {"td", "th"}


class _LineBuilder(HTMLParser):

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []
        self._buf = []
        self._skip_depth = 0
        self._in_row = False

    def _flush(self):
        text = " ".join("".join(self._buf).split())
        self._buf = []
        if text:
            self.lines.append(text)

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "tr":
            self._flush()
            self._in_row = True
        elif tag in CELL_TAGS and self._in_row:
            if "".join(self._buf).strip():
                self._buf.append(" | ")
        elif tag in BREAK_TAGS:
            self._flush()

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "tr":
            self._flush()
            self._in_row = False
        elif tag in BREAK_TAGS and not self._in_row:
            self._flush()

    def handle_data(self, data):
        if not self._skip_depth:
            self._buf.append(data)

    def close(self):
        super().close()
        self._flush()


def html_to_lines(html):
    builder = _LineBuilder()
    builder.feed(html or "")
    builder.close()
    return builder.lines


def extract_links(html):
    # (href, lank-text) for alla <a href> - anvands for artikelhittning.
    links = []

    class _Links(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self._href = None
            self._text = []

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                self._href = dict(attrs).get("href")
                self._text = []

        def handle_data(self, data):
            if self._href is not None:
                self._text.append(data)

        def handle_endtag(self, tag):
            if tag == "a" and self._href is not None:
                links.append((self._href, " ".join("".join(self._text).split())))
                self._href = None

    parser = _Links()
    parser.feed(html or "")
    parser.close()
    return links
