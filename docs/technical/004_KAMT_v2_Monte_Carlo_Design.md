# KAMT v2 — MONTE CARLO-ARKITEKTUR
## Design for nasta generations analysmodell

Version: 0.1 (utkast - ej godkand, oppna fragor kvarstar)
Status: Under diskussion
Foregangare: KAMT v1 (linjar viktad summa, se analysis/chaos_engine.py
och analysis/crowd_engine.py)

---

# Bakgrund och syfte

KAMT v1 rankar hastar via en linjar viktad summa: Total Score =
0.50*CrowdIndex + 0.50*ChaosIndex, dar varje komponent (13 stycken
totalt) bidrar oberoende av de ovriga.

KAMT v2 ersatter inte bara vikterna - den ersatter sjalva
berakningsmodellen. Malet ar en sannolikhetsfordelning per hast
(t.ex. Hast 1: 42 %, Hast 2: 12 %, Hast 3: 8 % ...) framtagen genom
Monte Carlo-simulering, dar vissa parametrar samverkar icke-linjart
istallet for att adderas var for sig.

Detta paverkar direkt Lager 2 (Analysis Engine) i
003_Restructuring_Plan.md - "Score Engine som vagd summa" ersatts av
den arkitektur som beskrivs har.

---

# Arkitekturens tre nivaer

Viktigt: detta ar INTE en sekventiell pipeline dar varje niva kors en
gang. Monte Carlo (Niva 3) ar den YTTRE loopen som omsluter allt -
den kor hela kedjan (dra startvarde fran Niva 1 -> kor genom Niva
2:s kopplingar -> registrera utfall) tusentals ganger. Niva 1 och 2
ar komponenter Monte Carlo anropar om och om igen, inte foregaende
steg i en pipeline.

## Niva 1: Grundvarden (Baseline)

Parametrar som INTE paverkas av loppets interna fysik/dynamik.
Definierar hastens fysiologiska status infor loppet samt marknadens
kollektiva forvantan.

**Parametrar:**
- Streckprocent
- Odds & oddsrorelse
- Experttips & social konsensus
- Hastform
- Stallform (tranarens segerprocent)

**Individualisering per hast:** varje hasts baskapacitet (tid per
kilometer) beraknas fran dess EGEN historik, inte ett generiskt
falt-/rassnitt. Bygger vidare pa samma grundprincip som redan finns
i historical_stats.py:tempo_differential() - men dar den idag
raknar ut en DIFFERENTIAL mot faltets snitt, behover Niva 1 ett
ABSOLUT baslinjevarde (sekunder per kilometer) per hast att utga
fran i simuleringen.

**Inte annu inkluderat (flaggat, ej beslutat):** alder, kon,
"career_earnings" samlas redan in men ingar varken i KAMT v1 eller
den har designen.

## Niva 2: Kopplingstabeller (Kaos & Dynamik)

Parametrar som INTE kan hanteras isolerat - de samverkar i matriser
och kan trigga kedjereaktioner inom en och samma simulering (t.ex.
en hast tar spets -> tvingar favoriten utvandigt -> favoritens
vinstchans kollapsar fran 60 % till 15 % i just den korningen).

**Fyra kopplingsmatriser:**

| Matris | Parametrar | Kaotisk kedjereaktion |
|---|---|---|
| A: Position & Start | Startspar x Kuskform x Tempo | Bra spar kraver offensiv kusk for spets; for hogt tempo straffar spetshasten, gynnar ryggar |
| B: Fysik & Underlag | Distans x Bana x Vader | Lang distans + regn -> tung bana, straffar ospeedade hastar, gynnar starka |
| C: Incidentrisker | Galopprisk x Spar x Bana | Galopprisk multipliceras vid svara startspar + snava/moddiga banor |
| D: Utrustning | Utrustning x Bana x Distans | Att definiera i detalj (oppen fraga - se nedan). Foljer samma monster som forsta exemplet: barfota + regn = negativt, rratt vagn + rratt spar = positivt |

**Vader som ny viktad parameter:** samlas redan in (SMHI, syns pa
kupongen) men har hittills bara varit informativt. Blir en riktig
viktad parameter via Matris B i KAMT v2.

**Utrustningsdata finns redan:** shod_front, shod_back,
shoe_changed, cart_type, sulky_changed samlas redan in av
horse_parser.py - inget nytt behover byggas for att fa fram raddatan
till Matris D, bara sjalva kopplingslogiken.

## Niva 3: Monte Carlo-motorn

Omsluter hela arkitekturen. Kor loppet ~10 000 ganger. I varje
enskild simulering:

1. Slumpa startvarden for osakra variabler, utifran de fordelningar
   Niva 1 satt (t.ex. kalibrerat mot Wisdom of the Crowd)
2. Applicera Niva 2:s kopplingsregler dynamiskt - inklusive
   positionskamp under loppets gang (vem tar ledningen, vem hamnar
   utvandigt) som paverkar utfallet inom just den korningen
3. Registrera slutresultatet for den korningen

Efter alla korningar: aggregera till en vinstsannolikhet per hast.

**Utdata jamfors mot Wisdom of the Crowd** (streckprocent) for att
hitta spelvarde - dar modellen och marknaden ar oense, och at vilket
hall.

---

# Learning Engine och kopplingstabellerna

Learning Engine ska over tid justera kopplingstabellernas
multiplikatorer baserat pa faktiska utfall, med individualiserade
ingangsvarden per hast fran historik.

**Kritisk forsiktighetsprincip (beslutad):** specifika
flerdimensionella kombinationer (t.ex. regn + barfota + bakspar) kan
ha mycket fa historiska observationer att lara ifran, vilket gor en
inlard multiplikator statistiskt opalitlig. Nar en kombination har
for lite historik for en palitlig inlard multiplikator, ska den
falla tillbaka pa en NEUTRAL effekt (ingen justering) istallet for
att Learning Engine gissar sig till en skakig siffra.

Detta speglar samma designprincip som redan finns i KAMT v1
(chaos_engine.py faller tillbaka pa neutralt varde 50 nar en
parameter saknar tillrackligt med data for en enskild hast) -
samma logik appliceras har pa kombinationsniva istallet for
parameterniva.

---

# Oppna fragor (ej beslutade an)

1. **Tabell D:s faktiska varden** - vilka konkreta multiplikatorer
   ska galla for vilka utrustnings-/bana-/distanskombinationer?
   Endast principen (egen matris) ar beslutad, inte innehallet.

2. **Tröskeln för "tillräckligt med data"** - hur många historiska
   observationer av en given kombination krävs innan Learning Engine
   litar på en inlärd multiplikator istället för att falla tillbaka
   till neutral? Inte definierat.

3. **Positionssimuleringens konkreta mekanik** - hur kedjereaktioner
   (häst tar spets → tvingar annan häst ut → chanser kollapsar) rent
   tekniskt ska modelleras och kodas. Det här är en betydligt större
   komponent än en uppslagstabell - flaggat som öppet, inte designat
   i detalj än.

4. **Generalitet kontra travspecifik** - hör parameter-uppdelningen
   (vilka fält är Nivå 1 vs Nivå 2) hemma i Lager 3 (Trav-modulen,
   eftersom fälten är travspecifika: startspår, galopprisk, sulky),
   medan själva Monte Carlo-MEKANISMEN (simulera N gånger, aggregera
   till fördelning) är den generella Lager 2-komponenten som andra
   framtida moduler (fotboll, aktiemarknad) återanvänder med sina
   egna parametrar? Detta knyter an till samma öppna fråga som redan
   fanns i 003_Restructuring_Plan.md om var gränsen mellan Lager 2
   och Lager 3 ska gå - men nu med ett konkret exempel att utgå från.

---

# Koppling till befintlig kod

| Ny komponent | Bygger vidare på |
|---|---|
| Nivå 1-baslinje per häst | historical_stats.py:tempo_differential() — samma grundidé, men behöver bli ett absolut värde istället för en differential |
| Matris D (Utrustning) | horse_parser.py samlar redan in shod_front, shod_back, shoe_changed, cart_type, sulky_changed |
| Matris B (Väder) | Väderdata samlas redan (SMHI), men går från rent informativ till en riktig viktad parameter |
| Neutral fallback vid gles data | Samma princip som redan finns i chaos_engine.py (NEUTRAL_SCORE=50) |
