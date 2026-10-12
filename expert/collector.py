from datetime import datetime, timezone

from expert.discovery import find_articles
from expert.fetcher import FetchBlocked
from expert.text import html_to_lines

#
# Data Collector-delen for experttips: hittar kallornas artiklar for ett
# spel, hamtar dem, later tolkaren gora text -> poster och sparar i
# Knowledge Base via DatabaseManager. Analyserar inget.
#
# Beroenden skickas in (fetcher, interpreter, db, lexikon, kallor) sa att
# allt kan testas utan natverk och sa att andra domaner kan ateranvanda det.
#


def game_type(game_id):
    # "V85_2026-10-10_6_5" -> "V85"
    return str(game_id).split("_")[0].upper()


class ExpertCollector:

    def __init__(self, fetcher, interpreter, db, sources, manual_articles=None, now=None, lexicon=None):
        self.lexicon = lexicon or getattr(interpreter, "lex", None)
        self.fetcher = fetcher
        self.interpreter = interpreter
        self.db = db
        self.sources = [s for s in sources if s.get("enabled")]
        self.manual = manual_articles or {}
        self._now = now or (lambda: datetime.now(timezone.utc).isoformat())
        self.last_tips = []

    def collect(self, game_id, game_date, track, roster):
        # roster: {lopp: {hastnummer: namn}}. Returnerar en lista med
        # rapporter (en per artikel eller per misslyckad kalla). Hela
        # korningen far EN hamtningstid, och tips fran flera artiklar fran
        # samma kalla slas ihop (hogsta sakerhet per lopp/hast/signal) -
        # annars skulle bara den sist hamtade artikeln raknas.
        reports = []
        gtype = game_type(game_id)
        fetched_at = self._now()
        self.last_tips = []
        for source in self.sources:
            name = source["name"]
            urls = self._article_urls(source, gtype, game_id, game_date, track, reports)
            merged = {}
            for url in urls:
                report, tips = self._read_article(name, url, roster)
                reports.append(report)
                for tip in tips:
                    key = (tip.leg, tip.horse_number, tip.signal)
                    if key not in merged or tip.confidence > merged[key][0].confidence:
                        merged[key] = (tip, url)
            self._store(name, game_id, game_date, fetched_at, merged, reports)
        return reports

    def _type_tokens(self, gtype):
        tokens = getattr(self.lexicon, "GAME_TYPE_TOKENS", {}) if self.lexicon else {}
        return tokens.get(gtype, (gtype.lower(),))

    def _article_urls(self, source, gtype, game_id, game_date, track, reports):
        name = source["name"]
        index_url = (source.get("index_urls") or {}).get(gtype)
        urls = []
        if index_url:
            try:
                html = self.fetcher.get_text(index_url)
                urls = find_articles(html, index_url, game_date, track, type_tokens=self._type_tokens(gtype))
            except FetchBlocked as exc:
                reports.append({"source": name, "url": index_url, "status": "blockerad", "detail": str(exc)})
                return []
            except Exception as exc:
                reports.append({"source": name, "url": index_url, "status": "fel", "detail": repr(exc)})
        if not urls:
            manual = self.manual.get(game_id, {}).get(name)
            if manual:
                urls = [manual]
        if not urls and index_url:
            reports.append({"source": name, "url": index_url, "status": "ingen artikel hittad"})
        return urls

    def _read_article(self, source, url, roster):
        report = {"source": source, "url": url}
        try:
            html = self.fetcher.get_text(url)
        except FetchBlocked as exc:
            report.update(status="blockerad", detail=str(exc))
            return report, []
        except Exception as exc:
            report.update(status="fel", detail=repr(exc))
            return report, []
        tips, stats = self.interpreter.interpret(html_to_lines(html), roster, source)
        report.update(status="ok", **stats)
        return report, tips

    def _store(self, source, game_id, game_date, fetched_at, merged, reports):
        if not merged:
            return
        for tip, url in merged.values():
            row = tip.to_dict()
            row.update(fetched_at=fetched_at, game_id=game_id, date=str(game_date)[:10], article_url=url)
            self.db.insert_expert_tip(row)
            self.last_tips.append(tip)
        for report in reports:
            if report.get("source") == source and report.get("status") == "ok":
                self.db.insert_expert_article({
                    "fetched_at": fetched_at, "game_id": game_id, "source": source,
                    "article_url": report["url"], "lines": report["lines"],
                    "legs_in_roster": report["legs_in_roster"],
                    "legs_with_tips": report["legs_with_tips"], "tips": report["tips"],
                    "unlinked_cues": report["unlinked_cues"],
                })
        self.db.commit()
