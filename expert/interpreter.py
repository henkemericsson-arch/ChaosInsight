import re
import unicodedata

from expert.tip import ExpertTip

#
# Tolkar text (rader) till ExpertTip-poster. Ingen extern AI - bara
# monster, ordlista och kanda entiteter (startlistan). Inga bedomningar.
#
# Indata:
#   lines   - lista av textrader (expert/text.py:html_to_lines)
#   roster  - {lopp: {hastnummer: hastnamn}} ur startlistan
#   lexicon - modul med ordlista/radmonster (t.ex. expert/trav/lexicon.py)
#   source  - kallans namn
#
# Utdata: (tips, report). report ger tolkningstackning sa att en artikel
# som inte forstods syns som sadan i stallet for att gissas.
#


def _normalize(text):
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"[^\w\såäö]", " ", text)
    return " ".join(text.split())


class _LegEntities:

    # Hittar kanda hastar i en mening for ett visst lopp.

    def __init__(self, horses, lexicon):
        self.numbers = set(horses)
        self.lexicon = lexicon
        self._names = []
        for number, name in horses.items():
            norm = _normalize(name)
            if len(norm) >= 3:
                self._names.append((number, re.compile(r"(?<!\w)" + re.escape(norm) + r"(?!\w)")))

    def find(self, sentence):
        norm = _normalize(sentence)
        found = {}
        for number, pattern in self._names:
            if pattern.search(norm):
                found[number] = 1.0
        for match in self.lexicon.NR_REFERENCE.finditer(sentence):
            number = int(match.group(1) or match.group(2))
            if number in self.numbers:
                found.setdefault(number, 0.8)
        for word, number in self.lexicon.NUMBER_WORDS.items():
            if number in self.numbers and re.search(r"(?<!\w)" + word + r"(?!\w)", sentence, re.IGNORECASE):
                found.setdefault(number, 0.6)
        return found


def _numbers_in(text, valid):
    return [int(n) for n in re.findall(r"\b\d{1,2}\b", text) if int(n) in valid]


def _split_sentences(line):
    parts = re.split(r"(?<=[.!?])\s+", line)
    return [p for p in parts if p.strip()]


class Interpreter:

    def __init__(self, lexicon):
        self.lex = lexicon

    def interpret(self, lines, roster, source):
        tips = {}
        report = {
            "lines": len(lines),
            "legs_in_roster": len(roster),
            "legs_with_tips": 0,
            "unlinked_cues": 0,
            "tips": 0,
        }
        entities = {leg: _LegEntities(horses, self.lex) for leg, horses in roster.items()}

        def add(leg, number, signal, confidence=1.0, rank=None, rank_of=None):
            if leg not in roster or number not in roster[leg]:
                return
            key = (leg, number, signal)
            existing = tips.get(key)
            if existing is None or confidence > existing.confidence:
                tips[key] = ExpertTip(
                    source=source, leg=leg, horse_number=number, signal=signal,
                    horse_name=roster[leg][number], rank=rank, rank_of=rank_of,
                    confidence=confidence,
                )

        current_leg = None
        current_category = None
        last_subject = {}

        for line in lines:
            row = self.lex.TABLE_ROW.match(line)
            if row:
                leg = int(row.group(1))
                numbers = _numbers_in(row.group(2), roster.get(leg, {}))
                for number in numbers:
                    add(leg, number, "system")
                    if len(numbers) == 1:
                        add(leg, number, "spik")
                continue

            bare = self.lex.TABLE_ROW_BARE.match(line)
            if bare and int(bare.group(1)) in roster:
                leg = int(bare.group(1))
                numbers = _numbers_in(bare.group(2), roster[leg])
                if numbers:
                    for number in numbers:
                        add(leg, number, "system")
                        if len(numbers) == 1:
                            add(leg, number, "spik")
                    continue

            category_hit = next(
                ((sig, pat.match(line)) for sig, pat in self.lex.CATEGORY_LINES if pat.match(line)), None
            )
            if category_hit:
                current_category = category_hit[0]
                # Posten kan stå på samma rad som kategorirubriken.
                remainder = line[category_hit[1].end():].lstrip(" :")
                entry = self.lex.ENTRY_WITH_LEG.match(remainder)
                if entry:
                    add(int(entry.group(2)), int(entry.group(1)), current_category)
                continue
            entry = self.lex.ENTRY_WITH_LEG.match(line)
            if entry and current_category:
                add(int(entry.group(2)), int(entry.group(1)), current_category)
                continue

            header = self.lex.LEG_HEADER.match(line)
            if header:
                current_leg = int(header.group(1))
                current_category = None
                last_subject = {}
                # Rubrikraden kan i sig innehalla text efter loppmarket - tolka resten.
                line = line[header.end():]
                if not line.strip():
                    continue

            leg = current_leg if current_leg in roster else None

            if leg is not None and self._structured(line, leg, roster[leg], add):
                continue

            # Utan aktuellt lopp (t.ex. ingressen) tolkas bara meningar som
            # sjalva namner ett lopp ("... i V85-4 dar 1 Mister ...").
            self._prose(line, leg, entities, roster, add, report, last_subject)

        report["tips"] = len(tips)
        report["legs_with_tips"] = len({t.leg for t in tips.values()})
        return list(tips.values()), report

    # --- strukturerade rader ---------------------------------------------

    def _structured(self, line, leg, horses, add):
        rank = self.lex.RANK_LINE.match(line)
        if rank:
            body = rank.group(1)
            tiers = list(self.lex.TIER_PART.finditer(body))
            if tiers:
                order = []
                for tier in tiers:
                    signal = "tier_" + tier.group(1).lower()
                    numbers = _numbers_in(tier.group(2), horses)
                    order.extend(numbers)
                    for number in numbers:
                        add(leg, number, signal)
                self._add_ranks(order, leg, add)
                return True
            numbers = _numbers_in(body, horses)
            if numbers:
                self._add_ranks(numbers, leg, add)
                return True
            return False

        for signal, pattern in self.lex.LABELED_LINES:
            match = pattern.match(line)
            if match:
                numbers = _numbers_in(match.group(1), horses)
                for number in numbers:
                    add(leg, number, signal)
                    if signal == "system" and len(numbers) == 1:
                        add(leg, number, "spik")
                return bool(numbers)
        return False

    @staticmethod
    def _add_ranks(order, leg, add):
        seen = []
        for number in order:
            if number not in seen:
                seen.append(number)
        for position, number in enumerate(seen, start=1):
            add(leg, number, "rank", rank=position, rank_of=len(seen))

    # --- fri text -----------------------------------------------------------

    def _prose(self, line, leg, entities, roster, add, report, last_subject):
        for sentence in _split_sentences(line):
            target_leg = leg
            leg_ref = self.lex.LEG_ANYWHERE.search(sentence)
            if leg_ref and int(leg_ref.group(1)) in roster:
                target_leg = int(leg_ref.group(1))
            if target_leg is None:
                continue
            ent = entities[target_leg]

            found = ent.find(sentence)
            cues = []
            for signal, pattern in self.lex.CUES:
                for match in pattern.finditer(sentence):
                    before = sentence[:match.start()]
                    if self.lex.NEGATION.search(before):
                        signal_out = self.lex.NEGATION_MAP.get(signal)
                        if signal_out:
                            cues.append(signal_out)
                    else:
                        cues.append(signal)
                    break

            if found and not cues:
                last_subject.clear()
                last_subject.update(found)
                continue
            if not cues:
                continue

            subjects = found
            confidence_scale = 1.0
            if not subjects:
                if len(last_subject) == 1:
                    subjects = dict(last_subject)
                    confidence_scale = 0.5
                else:
                    report["unlinked_cues"] += 1
                    continue
            elif len(subjects) > 1:
                confidence_scale = 0.6

            for number, base in subjects.items():
                for signal in cues:
                    add(target_leg, number, signal, confidence=round(base * confidence_scale, 2))

            if found:
                last_subject.clear()
                last_subject.update(found)
