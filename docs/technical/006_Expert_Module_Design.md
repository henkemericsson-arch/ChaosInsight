# 006 – Expertmodulen (Expert/Forum-signaler)

Status: FÖRSLAG – ej godkänt. Följer Bibelns ordning: arkitektur → dokumentation → struktur → implementation → test → versionslogg.

## 1. Bakgrund (som koden ser ut idag, repo 7152982)

- `analysis/expert_analyzer.py` gör **två saker** i samma klass: hämtar tips från `providers/travcash_provider.py` och `rekatochklart_provider.py` **och** räknar `expert_index` (andel källor som pekar ut hästen, 0–100).
- `config/expert_sources.py` är en **manuell** tabell game_id → artikel-slug/URL. Idag finns exakt ett spel (V85 2026-08-15). För alla andra spel hoppas experttips över, och `expert_index` blir aldrig satt. Det är orsaken till att `predicted_expert_index` är tomt – inte en loggningsbugg.
- `app.py` anropar `collect_tips()` och `apply()` direkt (avviker från 003: presentation ska vara tunn).
- Bibeln: *Data Collector* hämtar fakta från specialistkällor (Travcash, Travforum, Travsnack, framtida AI-källor) och analyserar aldrig. *Analysis Engine* har fristående moduler, bl.a. `ForumAnalyzer` och `ExpertAnalyzer`, som endast producerar sina egna metrics. Score Engine räknar samman metrics.

## 2. Mål

`expert_index` ska vara ett **resultat från ChaosInsights modell** på den samlade expertdatan från alla källor – inte en rå räkning – och modellen ska vara densamma oavsett domän. Källor är konfiguration per modul (trav har sina, en framtida fotbollsmodul andra).

## 3. Förslag till ansvarsfördelning

1. **Data Collector – `ExpertCollector` (per modul).** Hittar och hämtar texter/tips från källorna i `expert_sources` (konfiguration, inte kod). Ersätter manuell inmatning per game_id med automatisk artikelhittning där källan tillåter. Ett *provider*-gränssnitt per källa (finns redan: `base_provider.py`). Samlar bara fakta.
2. **Tolkning till strukturerad fakta** (parser-steg, ingen bedömning): fritext/analys/systemförslag → poster `{källa, spel, lopp, häst, typ: spik|favorit|rankad|ströms|avråder, rang, hämtad_tid, källa_url}`. Tolkaren kan vara regelbaserad eller språkmodell; beslut i avsnitt 5.
3. **Knowledge Base:** tabell `expert_tips` via `DatabaseManager` (ingen SQL utanför). Varje post har `fetched_at` → **point-in-time**; inget skrivs över.
4. **Analysis Engine – `ExpertAnalyzer` och `ForumAnalyzer` som AnalyzerModule** (registreras som övriga, körs via samma mekanism, inte direkt från `app.py`). Läser KB, beräknar per häst `expert_index` / `forum_index` med modellen: tips vägs per källa och per typ (t.ex. spik väger mer än strömsnamn); vikterna är data i parameterregistret, satta av användaren. Saknas tips för loppet: metric sätts inte (loggas som saknad, aldrig 0).
5. **Score Engine:** vikt för indexet som data (finns i dag som EXPERT 5 i Crowd).
6. **Learning Engine:** inga särskilda regler för experter. `expert_index` loggas i `metrics` som alla andra parametrar och utvärderas som dem (prognos mot utfall, 005). Learning Engine lär sig av systemets eget arbete, inte av källorna.

## 4. Strukturförslag

```
modules/trav/config/expert_sources.py     # källor (konfiguration)
modules/trav/collectors/expert_collector.py
providers/*_provider.py                    # en per källa, gemensamt gränssnitt
parsers/expert_tip_parser.py               # text -> strukturerade poster
foundation/database_manager.py             # insert/read expert_tips
analysis_engine/modules/expert_analyzer.py # AnalyzerModule: expert_index
analysis_engine/modules/forum_analyzer.py  # AnalyzerModule: forum_index
```
(Fysisk placering följer migreringsordningen i 003; tills `modules/trav/` finns ligger filerna där motsvarande ligger idag.)

## 5. Beslut

Beslutat (användaren, 2026-10-12):
- **Källorna lägger användaren till själv** i `expert_sources` (konfiguration, inte kod). Första listan: trav.se, rekatochklart.com, travcash.se, travstugan.se, atg.se, minadel.se, trav.tips, svenskatrav.n.nu, guiden.se.
- **Per källa hittar ChaosInsight dagens artiklar/tips själv** (via källans tips-översikt per speltyp), inte manuell slug per game_id. Manuell länk finns kvar som reserv.
- **Långsiktigt:** ChaosInsight ska även kunna *föreslå* nya källor (kandidater som användaren godkänner). Ej i första byggfasen.
- **Tolkning av text sker i en egen modul i ChaosInsight – ingen extern AI-tjänst, ingen API-nyckel** (avsnitt 7).
- Den samlade expertdatan är indata till `ExpertAnalyzer` som ger `expert_index` som parameter.

Att respektera: robots.txt/användarvillkor och rimlig hämtfrekvens. Gamla utlåtanden går sällan att hämta som de såg ut före loppet – data samlas framåt från installationsdagen (ingen backtest på experter).

## 6a. Första genomgång av källorna (2026-10-12, från startsidor; artikelinnehåll ej verifierat)

| Källa | Gratis tips? | Hitta dagens artikel | Anmärkning |
|---|---|---|---|
| trav.se | Ja, "allt är gratis" | `/speltips/speltyp/<v85|v86|grand-slam-75|...>` | Löpande text + systemförslag (stort/litet); hästnummer ej bekräftat |
| rekatochklart.com | Ja | `/trav/v85-tips/` m.fl. | "Analyser lopp för lopp" + komplett system |
| travcash.se | Ja | Startsidans lista "Gratis travtips" (titel, datum, tipster) | Loppvisa rubriker, rad "Streckar" med hästnummer, kort kommentar per häst. Mest strukturerad |
| travstugan.se | Ja, "alltid gratis" | Hub per speltyp (`/v85`, `/v86`, `/travtips`) | Krönikor/nyheter blandas med tips |
| svenskatrav.n.nu | Ja | Sida per speltyp | Ranking, spikar, outsiders; länkar vidare till andra tipskällor |
| atg.se | Delvis | Nyheter (`/nyheter/...`) | Mest nyheter/intervjuer, få rena tips; kan ge kontext men svag expertsignal |
| guiden.se | Delvis / ev. betalvägg | "Guiden Express V85: bana datum" | Kontrollera vad som är öppet |
| trav.tips | Oklart | – | Främst guider; inga omgångsspecifika tips synliga på startsidan |
| minadel.se | – | – | Hämtning avvisad av sajtens robots.txt vid första försök → utelämnas tills villkoren är kontrollerade |

## 7. Tolkningsmodulen (egen, utan extern AI)

Uppgift: text (artikel, tipslista) → strukturerade poster `{källa, spel, lopp, häst, typ, rang, säkerhet, hämtad_tid, url}`. Ingen bedömning av om tipset är bra – det gör Analysis/Learning Engine.

Metod (deterministisk, förklarbar, testbar):
1. **Segmentering:** dela artikeln i lopp (rubriker som "V85-3", "Lopp 3", "DD-1", avdelningsnummer) och därefter i stycken/meningar. Loppordning och datum stäms av mot startlistan (Race Collector).
2. **Entitetsigenkänning mot startlistan:** hästnamn och startnummer i det aktuella loppet är kända i förväg, så modulen letar efter *kända* hästar (exakt och normaliserad träff på namn, "nr 5", "5:an", "femman", "(5)"), inte efter okända namn. Det är den stora förenklingen som gör regelbaserad tolkning realistisk.
3. **Signalordlista (lexikon, data i konfiguration):** t.ex. spik/spikförslag/banker/pallkandidat → `spik`; favorit/ska vinna/klar vinnare → `favorit`; skräll/outsider/streckvärd/överraskare/pengar på → `skräll`; hör med/ström/bred gardering → `med`; avråder/överspelad/för lågt streck/hoppa över → `avråder`. Ordlistan har vikt per signal och kan utökas utan kodändring.
4. **Struktur-mönster:** rader av typen `Streckar: 5, 6, 9`, `Spik: 4`, rankade listor `1. Hästnamn 2. ...`, tabeller (per källa en liten mönsterfil).
5. **Närhetsregel och negation:** signal räknas för den häst som ligger närmast i samma mening; negationer ("inte", "knappast", "ingen spik") vänder tecknet. Flera hästar i samma mening delar på signalen.
6. **Säkerhet och täckning:** varje post får säkerhet (strukturerad lista > ordlistesignal > blotta omnämnande). Per artikel loggas tolkningstäckning (andel lopp med minst ett tolkat tips, andel omnämnda hästar som kunde kopplas). Låg täckning → artikeln flaggas, ingen gissning.
7. **Källadaptrar:** en liten klass per källa (hämtning + vilka mönster som gäller); tolkarkärnan är gemensam för alla källor och alla domäner – bara lexikon och startlista byts per modul.
8. **Test:** tolkningen testas mot en liten facit-uppsättning (några artiklar per källa som kontrollerats för hand). Lexikon och mönster ändras i konfigurationen av användaren/utvecklaren, inte automatiskt.

Förbehåll: regelbunden tolkning når inte språkmodellers nivå på fri prosa. Strukturerade källor (travcash, svenskatrav) bör ge hög täckning; fri text lägre. Det mäts och redovisas i stället för att antas.

## 6. Ordning

Dokument godkänns → `expert_tips`-tabell + collector + tolkare (utan påverkan på Total Score) → `ExpertAnalyzer` ger `expert_index` med vikt 0 (observe-only, loggas i `metrics`) → vikten sätts via det vanliga parameter-/Learning Engine-flödet (005) som för alla parametrar.

## 8. Som byggt (steg 1, 2026-10-12)

Status: godkänt av användaren. Byggt och testat i sandlåda mot kopior av repots filer (7152982); ej körd mot levande sajter.

- `expert/` (generell kärna): `tip.py` (ExpertTip), `text.py` (HTML → rader), `interpreter.py` (tolkaren), `scoring.py` (tips → index), `collector.py` (Data Collector-delen), `fetcher.py` (robots.txt, paus mellan anrop, User-Agent), `discovery.py` (hitta dagens artikel via datum/bana), `store.py` (senaste hämtning per källa). `expert/trav/lexicon.py` är travdata (loppmärken, radmönster, ordlista, signalvikter).
- Tolkaren hanterar de format som observerats: rubriker `GS75-1`/`V85-3`, `RANK: 4-1-6`, `Rankingen: A: 2 B: 1,4 C: 11`, `Min Vinnare:`, `Skrällen:`, systemtabell `Avd | Hästar`, samt fri text via ordlista med negation och hästnamn ur startlistan.
- `config/expert_sources.py`: källor som data (namn, vikt, översiktssida per speltyp), manuell reservlänk per game_id och `EXPERT_INDEX_ACTIVE = False`.
- Databas: tabellerna `expert_tips` (en rad per tolkad uppgift, med `fetched_at`) och `expert_articles` (tolkningstäckning per artikel); åtkomst bara via `DatabaseManager`.
- `analysis/modules/expert_analyzer.py` ersätter `analysis/expert_analyzer.py` (som både hämtade och räknade). Läser bara från databasen, registreras i `register_modules` före CrowdEngine. Med `EXPERT_INDEX_ACTIVE = False` sätts metric `expert_index_obs` (loggas via `metrics_json`, påverkar inte Total Score); med `True` sätts `expert_index` som CrowdEngine räknar in (vikt 5).
- Poängsättning: per källa och häst starkaste signalen + 25 % av övriga (tak 3), medel över de källor som har tips för loppet; saknade källor räknas inte som "nej".
- Insamling: `script/collect_expert_tips.py <game_id>` (stöd för `--dry-run`).

Begränsningar att känna till: `index_urls` för trav.se och travstugan är otestade; svenskatrav, guiden, atg och trav.tips är avstängda/tomma tills deras artikelstruktur kartlagts; minadel.se utelämnad (robots.txt). Tolkningen är verifierad på fixturer byggda efter travcash och rekatochklart, inte på levande sidor – tolkningstäckningen i `expert_articles` visar hur det faktiskt går.

### 8.1 Automatisk insamling (beslutad av användaren 2026-10-12)

`expert/auto_collect.py`: när ett spel ska analyseras (`web_app/app.py` efter `collector.collect(game)`) startas insamlingen i en bakgrundstråd. Sidan väntar inte; tipsen används nästa gång spelet analyseras. Hämtar inte om spelet hämtats de senaste 6 timmarna, inte för redan gångna spel och aldrig dubbelt för samma spel. Fel i insamlingen stoppar aldrig analysen. Manuell körning finns kvar: `script/collect_expert_tips.py <game_id> [--dry-run] [--show] [--debug-index]`.

### 8.2 Första verkliga körning (V85 Solvalla 2026-10-10, torrkörning)

Travcash (huvudartikel 8/8 lopp, "Tre tippar" 5/8, "Tidiga tankar" 2/8), rekatochklart 8/8, travstugan 8/8; 0 otolkade ledtrådar. trav.se hade inga artiklar publicerade för datumet. Format som tolkas: loppmärken (GS75-1, V85-3), `RANK:`, `Rankingen: A/B/C`, `Min Vinnare:`, `Skrällen:`, systemtabeller (med och utan loppmärke), kategorirubriker (Omgångens Bank/Korsdrag/Överstreckade) och fri text via ordlista.
