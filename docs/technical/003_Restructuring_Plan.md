# CHAOS INSIGHT RESTRUKTURERINGSPLAN
## Fran nuvarande struktur till fyra-lagersarkitekturen i 000_Blueprint.md

Version: 0.1 (utkast - ej godkand)
Status: Under diskussion

---

# Syfte

Det har dokumentet beskriver HUR vi tar oss fran dagens fungerande men
strukturellt avvikande kodbas till den fyra-lagersarkitektur som
000_Blueprint.md och Chaos_Insight_Bible.md beskriver, utan att
riskera det som redan fungerar och anvands aktivt (skarpa
spelbeslut).

Detta ar ett SKISS-dokument - avsett att diskuteras och andras innan
nagon kod skrivs, i enlighet med Bibelns egen ordning:
"Arkitekturen beslutas -> Dokumentationen uppdateras -> Strukturen
byggs -> Funktionaliteten implementeras."

---

# Oppen fraga innan detta laases fast

Anvandaren har flaggat en kommande central forandring av sjalva
analysstrukturen. Lager 2 (Analysis Engine) i den har skissen ar
darfor medvetet hallet GENERISKT - vikter och parameterlistor
beskrivs som DATA (konfiguration), inte som hardkodad struktur -
sa att den kommande forandringen kan monteras in utan ny
omstrukturering. Innan Lager 2 laases fast i detalj bor den
forandringen beskrivas.

---

# Lager 1: Foundation

Ansvarar for infrastruktur. Innehaller aldrig analyslogik eller
travspecifik kod.

## Foreslagen struktur

```
foundation/
    core_engine.py        - orkestrerar hela pipelinen
    logger.py              - ersatter spridda print()-satser
    configuration_manager.py - enda vagen in till config/
    database_manager.py    - enda vagen in till databasen
    file_manager.py         - enda vagen in till ovrig fillagring
    module_manager.py       - registrerar och startar Lager 3-moduler
    version_manager.py      - hanterar versionsnummer per CIDS
```

## Kartlaggning mot befintlig kod

| Ny komponent | Bygger vidare pa | Atgard |
|---|---|---|
| database_manager.py | services/db.py | Lindas in bakom ett gransnitt - ingen modul kor rasql direkt langre, bara via manager-metoder (t.ex. `get_horse_history(horse_name, distance)` istallet for direkta SQL-fragor i historical_stats.py) |
| file_manager.py | Direkta open()/json.load-anrop i app.py, prediction_logger.py, learning_engine.py, backfill_history.py | Alla filop lasningar/skrivningar samlas hbakom ett gransnitt. **Oppen fraga:** ska data/races/*.json flyttas in i SQLite (via database_manager) istallet for att fa en egen file_manager-vag? Det skulle radikalt minska antalet stallen som behover direkt filatkomst. |
| logger.py | Spridda print()-satser | Ny komponent. Migreras stegvis, modul for modul - inte pa en gang |
| configuration_manager.py | config/-mappen | Lindas in bakom ett gransnitt sa moduler slipper `from config.x import y` |
| module_manager.py | Finns inte | Ny komponent. Byggs forst nar det finns >1 modul att registrera (se Lager 3) - for tidigt att overengineera nu med bara Trav |
| version_manager.py | Finns inte | Ny, enkel komponent - en VERSION-fil eller databastabell enligt CIDS-schemat (0.x.x/1.x.x/2.x.x) |
| core_engine.py | Implicit spridd i app.py:s routes | Ny komponent som blir den enda vagen in till hela pipelinen: Race Collector -> ... -> Learning Engine |

---

# Lager 2: Analysis Engine

Ansvarar for att producera metrics. Aldrig en slutpoang, aldrig
travspecifik logik som inte ar generaliserad till "en parameter
med en vikt".

## Grundprincip (Bibeln, Grundfilosofi-kommentaren)

Berakningsmodellen ska vara densamma oavsett analysomrade. Det
som andras ar datan och parametrarna. Parametrar ska kunna
laggas till eller tas bort utan kodandringar pa flera stallen.

## Foreslagen struktur

```
analysis_engine/
    base.py                 - AnalyzerModule-gransnitt (abstrakt basklass)
    score_engine.py          - kombinerar metrics -> slutpoang, vikter som config
    parameter_registry.py    - lista over aktiva parametrar + vikter (data, ej kod)
```

## Kartlaggning mot befintlig kod - KRITISK ATGARD

**`analysis/chaos_engine.py` bryter idag mot grundprincipen.** Den
ar en enda klass med atta hardkodade komponenter (startspar 8%,
kuskform 8%, hastform 10%, stallform 5%, distans 5%, bana 4%,
galopprisk 5%, tempo 5%). Det maste delas upp i atta separata,
registrerbara AnalyzerModule-implementationer:

- StartPositionAnalyzer
- DriverFormAnalyzer
- HorseFormAnalyzer
- StableFormAnalyzer
- DistanceAnalyzer
- TrackAnalyzer
- GallopRiskAnalyzer
- PaceAnalyzer

Samma sak galler troligen `analysis/crowd_engine.py` (odds, streck-
procent, oddsrorelse, experttips, social konsensus - fem separata
komponenter idag troligen ocksa hopbakade).

Vikterna (8%, 8%, 10% osv.) flyttas fran hardkodad kod till
parameter_registry.py som data - sa att en framtida omvikning
(t.ex. anvandarens kommande "central forandring", eller det redan
namnda "Wisdom of Many Models"-konceptet med ~100 parametrar) blir
en konfigurationsandring, inte en kodandring.

`score_engine.py` fungerar redan konceptuellt ratt (kombinerar
metrics -> slutpoang, ingen egen analyslogik) - behover bara ta
emot vikterna fran parameter_registry.py istallet for hardkodade
0.50/0.50.

---

# Lager 3: Modules

Varje modul ar en sjalvstandig tillampning som anvander Lager 2:s
generella motor med sina egna parametrar och sin egen datakalla.

## Foreslagen struktur

```
modules/
    trav/
        module.py            - TravModule, implementerar ett gemensamt Module-gransnitt
        race_collector.py     - flyttad fran services/
        atg_client.py         - flyttad fran services/
        parsers/               - race_parser, horse_parser, result_parser, game_parser
        system_generator.py    - travspecifika begrepp (spikar/las/risk) hor hemma har
        config/                 - bet_types.py, bet_prices.py, expert_sources.py
```

## Kartlaggning mot befintlig kod

Det mesta av dagens `services/`, `parsers/`, `providers/` och delar
av `config/` ar i praktiken redan Trav-modulen - de behover flyttas
in under `modules/trav/` och exponera ett gemensamt grasssnitt
(`TravModule.get_available_actions()`, `TravModule.run(action,
params)`) som Core Engine/Module Manager kan prata med utan att
kanna till travspecifika detaljer.

**Detta loser direkt anvandarens Vision-kommentar:** nar en framtida
modul (t.ex. Football) laggs till blir det en ny mapp under
`modules/` som implementerar samma gransnitt - `app.py` behover
inte andras alls.

System Generator ar en oppen fraga: bor den vara en generell
"Decision Engine"-komponent i Lager 2 med travspecifik parametrering
i Lager 3, eller helt och hallet en Lager 3-komponent? Begreppen
den hanterar idag (spikar, las, ATG:s radpriser) ar rent
travspecifika, vilket talar for Lager 3 - men SJALVA
kombinatorik-logiken (budget/kostnadsberakning, trimning) ar
generell nog att kunna aterranvandas av andra moduler. Kan behova
delas i tva: en generell Lager 2-komponent for kombinatorik, och en
travspecifik Lager 3-komponent for sjalva reglerna.

---

# Lager 4: Presentation

Enbart granssnitt. Inga berakningar, ingen filatkomst, ingen
affarslogik.

## Kartlaggning mot befintlig kod - KRITISK ATGARD

`web_app/app.py` maste bantas radikalt. Allt av foljande ska bort
harifran och in i respektive ratt lager:

| Vad | Ligger idag i app.py | Ska till |
|---|---|---|
| Vaderformatering (SMHI-symbolkoder) | `_format_weather()` | modules/trav/ (travspecifikt presentationsformat, eller en generell weather-utility i foundation om flera moduler behover vader) |
| Xpress-detektering | `_detect_xpress()` | modules/trav/ (rent travspecifikt begrepp) |
| Tidszonskonvertering | `_format_local_time()` | foundation/ (generell utility, anvandbar av alla moduler) |
| Bakgrundstrad for historikpafyllning | `_maybe_start_automatic_backfill()`, `_run_backfill_in_background()` | foundation/core_engine.py eller en egen scheduler-komponent |
| Direkt JSON-lasning/skrivning | `list_predictions()`, `load_prediction()` | foundation/file_manager.py (eller database_manager.py om vi flyttar predictions till SQLite) |
| Risknivalogik, kaosvarde-visning | Mallarna i respektive route | Ligger kvar som visning, men datan ska komma fardigberaknad fran Core Engine - inte beraknas i mallen |

Efter det har ska `app.py` i praktiken bara innehalla: routes som
anropar Core Engine, tar emot fardig data, och renderar mallar.
Ingen `import services.X` for affarslogik langre - bara anrop mot
Core Engine/Module Manager.

Vision-kommentarens langsiktiga mal (valj analysomrade forst pa
startsidan, sedan travspecifik undersida) blir naturligt mojligt
nar app.py val bara ar ett tunt granssnitt ovanpa Module Manager.

---

# Migreringsordning (foreslagen)

Att skriva om allt pa en gang ar for riskabelt for en app som
redan anvands for skarpa spelbeslut. Foreslagen ordning, minst
riskabla forst:

1. **database_manager.py** - tunn inlindning av redan centraliserad
   services/db.py. Lag risk, ingen befintlig funktionalitet flyttas
   fysiskt, bara ett gransnitt lags ovanpa.
2. **logger.py** - ny komponent, migreras in gradvis (nya print()
   blir logger-anrop, gamla lamnas tills den fil de star i anda
   rors av annan anledning).
3. **Bryt upp ChaosEngine** till atta separata AnalyzerModule-
   implementationer + parameter_registry.py. Detta ar den storsta
   enskilda vinsten och forbereder direkt for den kommande
   analysstruktur-forandringen.
4. **Skapa modules/trav/** och flytta over services/parsers/
   providers dit. Mekanisk flytt + importvagar uppdateras.
5. **Bantar app.py** till ett tunt presentationslager, nu nar det
   finns nagot (Core Engine) att delegera till.
6. **module_manager.py + core_engine.py** som den formella
   orkestrerings-komponenten, nar TravModule finns som ett konkret
   exempel att bygga gransnittet mot.
7. **file_manager.py eller migrering av data/races/*.json till
   SQLite** - oppen fraga, se Lager 1-tabellen ovan.
8. **version_manager.py** - infors nar strukturen borjar stabiliseras,
   sa forsta versionsnumret betyder nagot.

---

# Fragor att besvara innan skissen laases fast

1. Vad ar den kommande centrala forandringen i analysstrukturen?
   Paverkar direkt hur parameter_registry.py ska se ut.
2. Ska data/races/*.json flyttas in i SQLite, eller ska en egen
   file_manager.py hantera JSON-filerna som idag?
3. Ska System Generator delas mellan Lager 2 (generell kombinatorik)
   och Lager 3 (travspecifika regler), eller ligga helt i Lager 3?
4. Migreringsordningen ovan - rimlig, eller vill du prioritera
   annorlunda (t.ex. borja med Lager 3-avgransningen istallet for
   Lager 1)?
