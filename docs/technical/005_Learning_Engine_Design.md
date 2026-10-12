# 005 – Learning Engine: självlärande analys

Status: **godkänd 2026-10-11** (steg 1 i utvecklingsordningen: arkitekturen beslutad). Etapp 1 byggd, se avsnitt 10.

## 1. Mål

Learning Engine ska gå från att bara *utvärdera* (prognos mot utfall) till att *dra slutsatser* och
*justera systemets parametrar automatiskt*, utan att enskilda lopp eller för lite data kan välta
viktningen. Allt ska kunna återställas.

Ramverket är generellt. Det som är travspecifikt (vilka parametrar som finns, vad ett utfall är)
ligger i adaptrar, inte i kärnan.

## 2. Princip: separera tre saker

| Ansvar | Modul | Gör |
|---|---|---|
| Utvärdera | `services/learning_engine.py` (finns) | Prognos mot utfall, loggar observationer. **Oförändrad.** |
| Analysera | `learning/analysis/` (ny) | Läser observationer, ger mått och slutsatser. Ändrar ingenting. |
| Justera | `learning/tuning/` (ny) | Föreslår, validerar, antar eller avvisar nya parametrar. Enda modulen som får skriva parametrar. |

Analys och justering känner inte till varandras internals. Analys levererar `Finding`-objekt, justering
konsumerar dem.

## 3. Etapper

### Etapp 1 – Kalibrering och rapport
- Brier score och log-loss för KAMT v1 (Total Score normaliserad till sannolikhet) och KAMT v2.
- Reliability-tabell: av hästar som fick 20–30 %, hur många vann faktiskt?
- Träffbild per rang: hur ofta vinner modellens rang 1, 2, 3 …
- Uppdelning per strategi, risknivå, bana, distans, startmetod.
- Jämförelse mot marknaden (odds/streck) som referens. Slår vi inte marknaden är det viktigaste att veta.
- Webbsida under jämförelsestatistiken, plus textrapport.

### Etapp 2 – Viktanalys
- Logistisk regression (vinst ja/nej) på delindexen per häst. Ger vilka signaler som faktiskt förklarar vinnare.
- Resultat: *rekommenderade vikter* med konfidensintervall, jämförda med nuvarande.
- Kräver att varje delsignal loggas per häst. **Lucka att kontrollera:** observationerna sparar idag
  `crowd/chaos/expert_index` och råvärden (odds, streck) men inte alla delpoäng (odds-, streck-, trend-,
  expertpoäng var för sig). De behöver läggas till innan etapp 2 går att köra fullt ut.

### Etapp 3 – Missanalys
Varje missat lopp klassas, och mönster summeras:
- Favorit förlorade (marknaden hade fel)
- Skräll (vinnare utanför gardering, högt odds)
- Valda hästar galopperade/diskades
- Strykning/reserv påverkade
- Spik/lås var fel, men hade garderat gått bra?
- KAMT v1 träffade men v2 missade, och tvärtom.

### Etapp 4 – Automatisk justering (med skydd)
Se avsnitt 4–5. Aktiveras först när etapp 1–3 finns och datamängden räcker.

## 3b. Regimer: systemet förändras medan det mäts

Systemets byggregler har ändrats under insamlingen (t.ex. spik/lås via odds, filtrering av strukna
hästar, trend som parameter, nytt standardvärde i KAMT v2). Äldre lopp mäter därför delvis ett *annat*
system än dagens. Learning Engine kan idag **inte** avgöra det själv: prediktionsfilerna sparar `saved_at`
men inte vilken version av generatorn eller analysen som gjorde dem.

Lösning i tre led:

1. **Hästnivå före systemnivå.** Etapp 1 mäter sannolikhet per häst (Total Score / KAMT v2-sannolikhet
   mot vinnare). Det är i stort sett opåverkat av ändringar i hur spikar, lås och gardering byggs, och
   påverkas bara av ändringar i själva analysen.
2. **Regimlista (nu).** `learning/trav/settings.py` har `REGIMES`: namn + första loppdatum. Rapporten delas
   upp per regim, så lopp från före en större ändring aldrig blandas med lopp efter. Datum hämtas ur
   `git log` (loppdatum används som approximation av genereringsdatum, eftersom observationerna inte
   sparar när systemet genererades).
3. **Versionsstämpel (framåt).** Varje ny prediktion och observation ska bära `generator_version` och
   `parameter_version` (parameteruppsättningen i avsnitt 4). Då behövs ingen gissning längre, och
   etapp 4 kan bara lära av lopp som gjorts med samma regim som den uppsättning som ska justeras.
   Kräver kolumnändring i `observations` (migrering) – egen leveransrad nedan.

Justering (etapp 4) får aldrig mata in lopp från äldre regimer än den aktuella basversionen.

## 4. Parameterlager

Alla justerbara värden flyttas ur koden till en **parameteruppsättning** (`parameter_sets` i SQLite):

```
version | created_at | parent | status (baseline|active|rejected|rolled_back) | params (JSON) | reason | evidence (JSON)
```

- **Version 0 = baseline**: dagens värden, oföränderlig. Reset går alltid att göra dit.
- Varje ändring skapar en *ny* version, ingen skrivs över. Full historik och förklaring (vilka mått motiverade ändringen).
- Koden läser aktiv uppsättning via en `ParameterProvider`. Saknas tabellen används baseline, så systemet fungerar som idag.

Första omgången justerbara parametrar (resten kan läggas till senare):
1. KAMT v1: delvikter (ODDS 20, STRECK 10, TREND 10, EXPERT 5 m.fl.) och Crowd/Chaos/Expert-vikter.
2. KAMT v2: kopplingskoefficienter (matriser A–D, korsmatris).

Senare, separat beslut: garderingsintervall (`BASE_COVERAGE_RANGE`), `RISK_FAVORITE_RATIO`, `FAVORITE_ODDS_MARGIN`.
Dessa har ett eget mål (kostnad kontra träff) och är svårare att optimera rent.

## 5. Skyddsräcken (kraven från användaren)

Justering får bara ske om **alla** villkor är uppfyllda:

1. **Tillräckligt med data.** Minst *N* utvärderade lopp totalt (förslag 300) och minst *M* nya sedan senaste justering (förslag 100). För parameter-grupper med mindre underlag (t.ex. per bana) justeras inget alls.
2. **Batch, aldrig per lopp.** Beräkningen sker på hela historiken, aldrig på senaste loppet. Ett enskilt lopp kan inte vända något.
3. **Statistisk signal.** Skillnaden måste vara större än bruset (bootstrap-konfidensintervall för förbättringen får inte inkludera 0).
4. **Dämpning.** Ny vikt = gammal + η · (föreslagen − gammal), η ≈ 0,2. Ändringarna sker långsamt.
5. **Stegtak.** Max ±10 % relativt per justering och max ±50 % totalt från baseline.
6. **Walk-forward-validering.** Kandidaten tränas på äldre lopp och måste slå nuvarande uppsättning på nyare lopp som den inte sett. Annars avvisas den (sparas som `rejected`).
7. **Avkylning.** Max en justering per M nya lopp.
8. **Automatisk återrullning.** Efter antagande jämförs live-utfallet för kandidat mot föregående över de nästa 50–100 loppen. Blir det klart sämre rullas den tillbaka (status `rolled_back`).
9. **Manuell reset.** Kommando och knapp i webben: återställ till baseline eller till valfri tidigare version. En reset *pausar* auto-justeringen tills du slår på den igen.
10. **Spårbarhet.** Varje beslut (antaget, avvisat, återrullat) loggas med skäl i versionsloggen.

Ingen justering har effekt på redan sparade system. Utvärderingar använder alltid de parametrar systemet
hade när det genererades (versionsnumret sparas i varje prediktionsfil).

## 6. Filstruktur (förslag)

```
learning/
  __init__.py
  metrics.py              # Brier, log-loss, träffgrad, bootstrap
  observation_reader.py   # läser observationstabellen, ger rena dataset
  analysis/
    calibration.py        # etapp 1
    weight_analysis.py    # etapp 2
    miss_analysis.py      # etapp 3
    findings.py           # Finding-datatyp
  tuning/
    parameter_store.py    # parameter_sets, versionering, reset
    parameter_provider.py # läsning för resten av systemet
    guard.py              # skyddsräckena i avsnitt 5
    adjuster.py           # föreslår och antar/avvisar uppsättningar
    rollback_monitor.py   # punkt 8
  trav/
    parameter_schema.py   # travspecifika parametrar och gränser (adapter)
```

`learning/` är generellt; `learning/trav/` är den första implementationen.

## 7. Leveransordning

1. Dokumentet godkänns (klart).
2. Etapp 1: `metrics`, `observation_reader`, `calibration`, rapport (**klart, CLI**; webbsida följer när `app.py` kan ses). Inga beteendeändringar.
3. Versionsstämpel (`generator_version`/`parameter_version`) i prediktioner och observationer, samt loggning av delpoäng per häst (förutsättning för etapp 2 och 4).
4. Etapp 2 och 3.
5. Parameterlager (`parameter_store`/`provider`) med baseline = dagens värden. Fortfarande inga beteendeändringar.
6. Etapp 4: guard, adjuster, rollback, reset. Levereras **avstängd som standard** och slås på när datamängden räcker.
7. Versionslogg uppdateras efter varje etapp.

## 8. Ärliga förbehåll

- Idag finns relativt få utvärderade lopp. Etapp 1 visar hur mycket data som faktiskt finns; tröskelvärdena (300/100) bör justeras efter det.
- Travresultat är brusiga. Även ett bra system träffar sällan 8 av 8, så förbättringar syns långsamt och måste mätas på hästnivå (log-loss) snarare än på hela systemets träff.
- Marknaden (odds/streck) är redan en mycket stark prediktor. Risken är att "inlärning" bara lär sig kopiera den. Därför jämförs alltid mot marknad som referens i etapp 1.
- Galopp­banor (Bro Park m.fl.) ligger kvar i datat och bör filtreras bort före etapp 1, annars förorenas statistiken.

## 9. Öppna beslut

- Tröskelvärden i avsnitt 5 (förslag: N=300, M=100, η=0,2, tak ±10 % / ±50 %).
- Om garderingsparametrar ska vara med i första auto-omgången (förslag: nej).

## 10. Etapp 1 – som byggd

- `learning/metrics.py` – Brier, log-loss, vinnarrang, reliability, bootstrap-CI (ren matematik).
- `learning/observation_reader.py` – bygger avgjorda lopp ur observationsrader. Tar senaste *hela* observationsomgången per lopp och modell (continuous/legacy räknas som KAMT v1), utesluter strukna hästar, galoppbanor, ej avgjorda lopp och rader utanför datumintervall.
- `learning/analysis/calibration.py` – sammanfattning, parvis jämförelse mot marknad (odds/streck) med konfidensintervall, kalibreringstabell, vinnarens rang, uppdelning per bana/distans/start.
- `learning/analysis/calibration_report.py` – ren textformatering.
- `learning/trav/settings.py` – travspecifikt: modell↔strategi, galoppbanor, distansklasser, regimer, tröskel.
- `DatabaseManager.observations_for_analysis()` – enda databasåtkomsten (ren läsning).
- `script/learning_calibration_report.py` – kör rapporten; sparar även JSON i `data/reports/`.

Normalisering: modellens poäng skalas om till sannolikheter per lopp (andel av summan). För KAMT v1 är Total Score ingen äkta sannolikhet, så mätningen visar hur väl *rangordningen och styrkeförhållandena* stämmer, inte att poängen är en kalibrerad procent. Marknadens sannolikheter = normaliserat 1/odds respektive normaliserad streckprocent.

### Tillägg efter första riktiga körningen (299 KAMT v1-lopp, 172 KAMT v2-lopp)

- **Skärpejustering.** Total Score är ingen sannolikhet; "andel av summan" blev för platt (de flesta hästar landade i 5–10 %), vilket gav kraftigt överdrivet dålig log-loss för KAMT v1 trots god rangordning. Rapporten anpassar nu en exponent k per prediktor (p^k, normaliserat) och redovisar både rå och skärpejusterad jämförelse. Skärpejusterad är den rättvisa jämförelsen av rangordningens kvalitet.
- **Odds 0 = struken.** Observationer utan korrekt `actual_scratched` (äldre fel i resultattolkningen) fångas nu via odds <= 0, så de inte förorenar fältet eller marknadsmåttet.
- **Okända strategier redovisas per namn** i stället för som en klump.
- **Utveckling per ISO-vecka** (modell mot marknad på samma lopp) för att se förändring över tid även innan `REGIMES` är ifyllt.
- **Top1 på exakt samma lopp** visas vid varje parvis jämförelse.

## 11. Etapp 1b – huvudmått: urval av spik/lås och täckning

Utgångspunkt (användarens): marknaden har nästan alltid en klar favorit per lopp, och spikar/lås bör
därför spegla marknaden. ChaosInsights uppgift är att välja **vilken favorit (vilket lopp) som är
säkrast att spika och vilka lopp som ska låsas** enligt vår metod. Lopp utan klar favorit är lämpade
för bred gardering. Ett lopp är bara ett misslyckande när vinnaren inte fanns bland de valda hästarna.

Därför är log-loss (avsnitt 10) ett komplement, och följande är huvudmått:

1. **Spik- och låsurval.** Inom varje spel rankas loppen efter ett kriterium; mäts hur ofta favoriten
   (spik) respektive någon av de två främsta favoriterna (lås) vann i de s högst rankade loppen
   (@1, @2, @3), samt inom-spel-AUC. Kriterier: Total Score (råpoäng, som systemet använder), Total
   Score (andel), marknadens odds, marknadens streck, lågt kaosvärde. Slump och marknadens odds är
   referenser. Skillnader redovisas med bootstrap över spel.
2. **Kaosvärde.** Delar lopp i tredjedelar efter kaosvärde och visar favoritträff och top-2/top-3-täckning.
   Om kaosvärdet fungerar faller träffen med stigande kaosvärde, vilket motiverar bredare gardering.
3. **Täckning.** Andel lopp där vinnaren fanns bland systemets valda hästar, per strategi och bredd,
   jämfört med marknadens topp-N med exakt samma antal hästar. Redovisar särskilt lopp där systemet
   valde annorlunda än marknaden.

Förbehåll: täckning mäts på senast utvärderade systemet per strategi och lopp (observationstabellen).
Att mäta alla risknivåer och antal rätt/utdelning per system kräver prediktionsfilerna (`saved_at`,
`outcome`) och blir nästa steg, tillsammans med datering av regimer via `saved_at`.

Filer: `learning/analysis/leg_analysis.py`, `leg_report.py`, `script/learning_leg_report.py`.

### Första resultat etapp 1b (2026-10-11; 38 spel / 256 lopp för KAMT v1, 27 spel för KAMT v2)

- **Kaosvärdet fungerar som svårighetsmått (KAMT v1).** Favoritträff 49 % / 41 % / 25 % och marknadens topp-3-täckning 81 % / 71 % / 55 % från lägsta till högsta tredjedel. Stödjer principen att lopp utan klar favorit får bred gardering.
- **Täckning KAMT v1 ≈ marknaden.** 72,0 % mot 70,9 % (skillnad +1,0 pe, 95 % CI -3,4..+5,4). Lås (bredd 2): 71,4 % mot 67,9 %. Spik (bredd 1): 43,5 % mot 45,7 %. Upplösningen vid ca 300 lopp är ungefär ±4-5 pe; för att upptäcka en fördel på 2 pe krävs i storleksordningen 1 400 lopp.
- **Spikurval.** Alla kriterier slår slump (ca 52 % mot 40 %), men Total Score (AUC 0,61) är svagast, marknadens odds 0,66 och lågt kaosvärde 0,69. Skillnaderna är inte statistiskt säkerställda. Faktisk spikträff i systemen är ca 44 % (46 lopp) – spikvalet är den enskilt viktigaste hävstången. Ingen ändring i systemet på så här litet underlag.
- **KAMT v2 sämre.** Täckning 59,9 % mot marknadens 69,1 % (-9,2 pe, CI -15,0..-3,4). Valde annorlunda än marknaden i 141 av 207 lopp och hade där vinnaren i 53 % mot marknadens 67 %.
- **Principförtydligande (användaren):** `backfill_starts` är *indata till analysen* (parametrar för beslutsfattande). Learning Engine lär sig av **ChaosInsights egna prediktioner mot utfall**: vad som gick rätt respektive fel. Ingen separat modell tränas på historiken.
- **Möjlig senare utvidgning – backtest:** återskapa ChaosInsights *egna* prediktioner retroaktivt på historiska lopp så att Learning Engine får fler av sina egna prediktioner att lära av. Kräver point-in-time-säkerhet (analysen får bara använda data från före loppets datum; alla historikfrågor måste ha datumgräns) samt att komponenter som saknar historik (oddstrend, expert) hanteras. Ej beslutat.
- **Nästa steg (förslag):** Etapp 3 – missanalys på de egna prediktionerna (träff/miss per lopp, orsaksklassning, jämförelse mellan missade vinnare och valda hästar).

## 12. Etapp 3 – missanalys (byggd)

Lär av de egna prediktionerna (principen i avsnitt 11). Per strategi (continuous, legacy, KAMT v2) och lopp med sparade val:

1. **Träff/miss** och typ av träff (spik, lås, gardering).
2. **Orsaksklass för miss** (första träffande regel): favoriten vann men valdes bort; skräll (vinnarens odds >= 10); knapp miss (vinnaren strax utanför valda i modellens rang); blindfläck (mellanodds, lågt rankad); övrigt.
3. **Träff per vinnarens oddsband** – hur väl skrällar täcks.
4. **Träff och bredd per kaosvärdetredjedel** – garderar vi bredare när det är svårt?
5. **Galopp/diskning bland valda hästar** – otur snarare än modellfel.
6. **Egenskapsjämförelse:** vad skiljer den vinnande hästen från de valda hästarna (odds, streck, startspår, förarens/tränarens/hästens form, prispengar, sko- och sulkyändring), för missar respektive träffar, med bootstrap-CI. Hypotesgenerering; ändrar inget automatiskt.

Filer: `learning/analysis/miss_analysis.py`, `miss_report.py`, `script/learning_miss_report.py`. `COVERAGE_STRATEGIES` ligger nu i `learning/trav/settings.py`.

## 13. Hästnivå – under-/övervärderas vissa hästar återkommande? (byggd som diagnos)

Fråga (användaren): är en häst återkommande oddsad som skräll men presterar bättre än marknaden tror,
eller återkommande favorit/trea i marknaden som vinner oftare respektive sällan än rangen säger?

Metod (`learning/analysis/horse_residual.py`, `script/learning_horse_report.py`):
- Läser `backfill_starts` som ström (kronologiskt), tar bort dubbletter (samma lopp under flera spel), utesluter galoppbanor.
- Marknaden kalibreras först (exponent k) så att marknadens allmänna skevhet (långskott/favoriter) inte tolkas som hästspecifik.
- Per häst: kvot = (vinster + prior) / (förväntade vinster + prior), dragen mot 1 vid kort historik, antingen över hela historiken eller med avtagande vikt, och antingen över alla starter eller **per roll** (favorit / tvåa-trea / övriga).
- **Strikt framåtriktat:** kvoten använder bara äldre lopp. Testas dels som tilt av marknadens sannolikhet (kvot^beta, delta log-loss med CI), dels som "kvot nästa start" per kvotgrupp och oddsband/roll.
- Rollspecifik tilt testas per roll så att en effekt som bara finns för favoriter inte späds ut.

Förbehåll: marknader är i regel effektiva; ett varaktigt, hästspecifikt mönster är en hypotes som ska bevisas, inte antas. Namnkollisioner (samma hästnamn) och att odds i historiken är slutvärden kan påverka. Om signal finns blir nästa steg en analysmodul ("marknadsresidual") i Analysis Engine som Score Engine kan använda; annars förkastas hypotesen. Ingen systemändring görs av diagnosen.

## 14. Marknadsresidual som analysparameter (arkitekturbeslut, ej byggd)

Beslut (användaren): hästnivåmönstret under-/övervärdering ska vara en **parameter i analysdatan** som modellen använder för sina prediktioner, inte bara en Learning Engine-diagnos.

Ansvarsfördelning (följer informationsflödet):
- **Analysis Engine** beräknar måttet `market_residual` per häst (ny analysmodul, ett ansvar). Indata: hästens historik i Knowledge Base (`backfill_starts` + egna utfall). Utdata: `horse.set_metric("market_residual", ...)` samt rollvarianten (`market_residual_role`: favorit / tvåa-trea / övriga utifrån hästens marknadsrang i det aktuella loppet).
- **Score Engine** viktar måttet i Total Score. Vikten är en parameter, startvärde **0** (observe-only).
- **Learning Engine** äger beslutet om vikten: den får bli > 0 först när walk-forward-testet (avsnitt 13) visar signifikant förbättring (CI för delta log-loss helt under 0 och bättre täckning i avsnitt 11) och sätts då inom de skyddsräcken som gäller för all automatisk justering (dämpning, minsta datamängd, reset).

Krav:
1. **Point-in-time:** vid analys av ett lopp används bara starter med datum före loppets datum. Annars läcker facit.
2. **Samma definition som diagnosen:** kalibrerad marknad (k), krympt kvot (W+prior)/(E+prior), valfri avtagande vikt. Logik delas via en gemensam modul (ingen duplicerad kod); diagnosen och analysmodulen anropar samma funktioner.
3. **Loggas för varje häst** tillsammans med övriga mått, så att Learning Engine kan utvärdera den mot utfall även medan vikten är 0.
4. **Kort historik ger neutralt värde** (kvot 1.0, via prior), aldrig 0 – undviker att nya hästar straffas.
5. **Effekten begränsas** (tilt kvot^beta med beta och tak från Learning Engine) så att en enskild häst inte kan dominera.

Ordning: (a) kör `learning_horse_report.py` på riktig data – avgör om det finns signal; (b) finns signal: bygg gemensam modul + analysmodul + loggning, vikt 0; (c) samla utfall i skuggläge; (d) Learning Engine föreslår/sätter vikt. Finns ingen signal förkastas parametern och dokumentet uppdateras.

### 14.1 Utfall av steg (a), 2026-10-11 – hypotesen förkastas (tills vidare)

Körning på riktig data (71 201 lopp, 5 år, k = 1,1, dubbletter och galoppbanor borta):
- Tilt med hästens kvot (kvot^beta) gav **högre** log-loss än ren kalibrerad marknad för alla beta (−0,5 … 2,0), i alla varianter (hela historiken, avtagande vikt 0,95, per roll). Ingen enda kombination förbättrade, och flera är säkerställt sämre. Större beta ger större försämring – mönstret är brus, inte signal.
- "Nästa start" per kvotgrupp visar inget monotont samband: hästar med hög respektive låg kvot före starten presterar likvärdigt i nästa start. Kvarvarande avvikelser (t.ex. övriga/kvot 0,85–1,15: 1,07) ligger i mittgruppen, alltså marknadens allmänna skevhet, inte hästspecifikt. Favoriter vinner dock generellt något oftare än oddsen säger (1,05, z = +11) och skrällodds något mer sällan (0,90) – redan hanterat av kalibreringen k.
- Beslut: `market_residual` byggs **inte** som viktad parameter nu. Arkitekturen i avsnitt 14 står kvar som reserverad plats; testet kan köras om när mer data finns eller med andra definitioner (t.ex. per tränare/förare, per distans/bana). Ingen kod i Analysis/Score Engine ändrad.

## 15. Etapp 2, steg 1 – logga delmått och kodversion (byggd)

Problem: bara slutpoängen och två index sparades och ingen kodversion följde med. (`predicted_expert_index` är tomt eftersom expertmodulen ännu inte levererar något index – det är avsiktligt, se 15.1.) Utan delmått går det inte att se vilka signaler som bär vikt (etapp 2), och utfall från olika systemversioner kan inte hållas isär.

Lösning:
- `foundation/run_info.py`: `code_version()` (kort git-hash, `-dirty` vid ej incheckat), `metrics_to_dict` (bara tal), `dump_metrics`/`load_metrics`.
- Prediktionsfilen får `code_version` och per häst `metrics` (hela `horse.metrics`; `expert_index` rörs inte).
- `observations` får kolumnerna `metrics_json` och `code_version`; `migrate_schema` lägger till dem i befintliga databaser. Äldre rader har dem tomma (kan inte återskapas).
- Learning Engines läsare (`observation_reader`) ger varje häst `metrics` och varje lopp `meta.code_version`.
- Installeras med idempotent `script/patch_log_metrics.py`.

Nästa: etapp 2a (regression på delmåtten) kan göras först när det finns tillräckligt många utvärderade lopp med `metrics_json`; tills dess samlas data.

### 15.1 Expertindex (förtydligande)

`expert_index` är tomt för att expertdelen ännu inte är byggd, inte på grund av en loggningsbugg. Enligt 003 är experttips en separat komponent (`experttips`, EXPERT-vikt 5 i Crowd) och källorna ska ligga i en egen modul (`config/expert_sources.py`); `app.py` anropar `ExpertAnalyzer.collect_tips()/apply()`. Loggningen ändrar inget där: delmåtten sparas bara om de finns i `horse.metrics`, och inget skrivs för `expert_index` om modulen inte satt det. Expertmodulen är sedan byggd enligt `006_Expert_Module_Design.md`; indexet loggas som `expert_index_obs` (observe-only) tills Learning Engine visat att det tillför något.

## 16. Parameterlager (steg 5 i leveransordningen, byggt)

Mål: flytta alla justerbara vikter ur koden till en versionerad parameteruppsättning, så att Learning Engine (etapp 4) senare kan föreslå, anta, rulla tillbaka och återställa dem utan kodändringar. **Ingen beteendeändring:** med baseline (version 0) ger systemet exakt samma Total Score som före ändringen.

### 16.1 Arkitektur

```
Analysis Engine (Crowd/Chaos) och ScoreEngine
        │  läser vikter
        ▼
ParameterProvider  ── ögonblicksbild av aktiv uppsättning (aldrig SQL i motorerna)
        │
        ▼
ParameterStore  ── versionering, baseline, status
        │
        ▼
DatabaseManager (tabellen parameter_sets i Knowledge Base)
```

- `learning/tuning/parameter_store.py` – `ParameterStore`: skapar baseline (version 0, oföränderlig), lägger till nya versioner (`add`), ändrar status (`set_status`, aldrig på version 0), hämtar aktiv uppsättning. All SQL går via `DatabaseManager`.
- `learning/tuning/parameter_provider.py` – `ParameterProvider`: läser aktiv uppsättning till en oföränderlig ögonblicksbild (`ParameterSet`) och ger `value(namn)`, `group(prefix)` och `version`. Saknas tabellen eller går läsningen fel används baseline, så systemet fungerar som förut. `refresh()` läser om; `app.py` anropar den i början av varje spelanalys.
- `learning/trav/parameter_schema.py` – de travspecifika parametrarna och deras baseline-värden (adapterlagret; den generella koden i `learning/tuning/` känner inte till något travspecifikt). `learning/trav/parameters.py` ger standardprovidern.
- Tabell `parameter_sets`: `version | created_at | parent | status (baseline|active|rejected|rolled_back) | params (JSON) | reason | evidence (JSON)`. Aktiv uppsättning = senaste versionen med status `active`, annars baseline.

### 16.2 Parametrar (första omgången)

| Grupp | Namn (baseline) |
|---|---|
| crowd | odds 20, streck 10, trend 10, expert 5 |
| chaos | start_position 8, driver_form 8, horse_form 10, trainer_form 5, distance 5, track_condition 4, gallop_risk 5, tempo 5 |
| score | crowd 0,50, chaos 0,50 |

Klassernas konstanter (`CrowdEngine.ODDS_WEIGHT` m.fl.) tas bort; baseline finns på ett ställe (schemat). KAMT v2:s kopplingskoefficienter och garderingsparametrarna läggs till i ett senare steg (se avsnitt 4).

### 16.3 Versionsstämpel

- `parameter_version` sparas i varje prediktionsfil och i `observations` (ny kolumn, `migrate_schema`), så att utfall alltid kan hållas isär per parameteruppsättning.
- Utvärderingar använder den uppsättning systemet hade när det genererades (regimlogiken i avsnitt 3b gäller `code_version` och `parameter_version` tillsammans).

### 16.4 Delpoäng per häst (förutsättning för etapp 2a)

Luckan som avsnitt 3 pekade ut åtgärdas här. Motorerna sparar nu varje delpoäng som ett mått på hästen, och eftersom hela `horse.metrics` loggas (avsnitt 15) hamnar de i `metrics_json` utan fler ändringar:

- Crowd: `crowd_odds_score`, `crowd_streck_score`, `crowd_trend_score` (när trend finns); expert loggas som `expert_index_obs` (eller `expert_index` när den är aktiv).
- Chaos: `chaos_start_position_score`, `chaos_driver_form_score`, `chaos_horse_form_score`, `chaos_trainer_form_score`, `chaos_distance_score`, `chaos_track_condition_score`, `chaos_gallop_risk_score`, `chaos_tempo_score` samt `data_coverage_n` (antal av 8 komponenter med riktig historik; saknad komponent har fått neutralt värde 50, vilket regressionen ska se som modellen såg det).
- Äldre loggade lopp saknar delpoängen och kan inte återskapas.

### 16.5 Verktyg

`script/learning_parameters.py` visar aktiv uppsättning, alla versioner och skapar baseline vid behov. Ändrar inget annat.

### 16.6 Testkrav

Ekvivalens: med baseline ska `crowd_index`, `chaos_index` och `total_score` vara identiska med före ändringen för samma indata. Dessutom: en ändrad uppsättning ger förväntad effekt, saknad tabell ger baseline, och version 0 går inte att ändra.

Nästa: etapp 2a (viktanalys) när det finns tillräckligt många utvärderade lopp med delpoäng; sedan etapp 4 (guard, adjuster, rollback, reset).

## 17. Etapp 2a – viktanalys (byggd)

Svarar på tre frågor, utan att ändra något i systemet:

1. Vilka delsignaler förklarar faktiskt vem som vinner?
2. Slår anpassade vikter dagens Total Score på nyare lopp som modellen inte sett?
3. Tillför expertindexet något *utöver* dagens Total Score?

### 17.1 Modell

Ett lopp har exakt en vinnare, så rätt modell är en **conditional logit**: sannolikheten att häst *i* vinner är `exp(β·x_i) / Σ_j exp(β·x_j)` över hästarna i loppet, där `x` är hästens delpoäng (de mått som sedan avsnitt 16.4 loggas i `metrics_json`). Anpassas med Newton–Raphson och en liten ridge-straffterm (`WEIGHT_RIDGE`), på standardiserade delpoäng så att koefficienterna går att jämföra. Ren Python, inga externa bibliotek.

Delpoäng som används (alla 0–100): `crowd_odds_score`, `crowd_streck_score`, `crowd_trend_score`, samt de åtta `chaos_*_score`. Saknad trend (loppet saknar trenddata) ersätts med neutralt 50, som i Crowd-beräkningen när trend finns men hästen saknar värdet. Lopp där någon häst saknar någon delpoäng (äldre lopp, före avsnitt 16) räknas inte med och redovisas som bortfall.

### 17.2 Jämförelse mot nuvarande modell (walk-forward)

- Loppen sorteras på datum. De äldsta 70 % är träning, de nyaste 30 % test (aldrig slumpmässig uppdelning – framtiden får inte läcka in).
- **Nuvarande modell** = den loggade Total Score, omvandlad till sannolikhet med en temperatur `τ` som anpassas på träningsdelen (`softmax(τ · Total Score)`). Det är samma sak som modellen faktiskt använde.
- **Anpassad modell** = conditional logit tränad på träningsdelen.
- Mått: medel-log-loss per lopp på testdelen. Skillnaden (anpassad − nuvarande) får ett bootstrap-konfidensintervall över testloppen.
- **Verdikt:** anpassade vikter räknas bara som bättre om hela intervallet ligger under 0 (motsvarar skyddsräcke 3 och 6 i avsnitt 5). Annars: "ingen påvisad förbättring".

### 17.3 Koefficienter och förslag

- Slutlig anpassning på alla lopp. Konfidensintervall per koefficient med bootstrap över lopp (varm start från hela anpassningen).
- Koefficienter jämförs med nuvarande effektiva vikter. Nuvarande effektiv vikt för signal *j* = `score.<grupp> · vikt_j / summa(gruppens vikter)` (Crowd räknas med trend, utan expert).
- **Förslag i parametrarnas termer** (travadaptern, `learning/trav/weight_features.py`): negativa koefficienter sätts till 0; `score.crowd`/`score.chaos` sätts efter respektive grupps andel av summan; vikterna inom gruppen sätts proportionellt mot koefficienterna men behåller gruppens nuvarande summa. Mappningen är testad åt båda hållen (nuvarande parametrar → koefficienter → samma parametrar). Förslaget är **information**; inget skrivs till parameterlagret (det är etapp 4:s uppgift, med skyddsräcken).

### 17.4 Expertindexets mervärde

Frågan är om `expert_index_obs` tillför information bortom Total Score. Modellen blir `softmax(τ · Total Score + γ · expert)` med `τ` fast från avsnitt 17.2 och en enda fri koefficient `γ` (per 10 indexpoäng). Redovisas med bootstrap-konfidensintervall för `γ` och för förbättringen i log-loss per lopp. Bara lopp där expertindex finns för alla hästar används. Slutsatsen "tillför information" kräver att *både* intervallet för `γ` och intervallet för förbättringen i log-loss ligger helt över 0; bara det förra ger "antydan, ej belagt". Först då finns skäl att aktivera indexet (`EXPERT_INDEX_ACTIVE`, se 006) – och även då är det ett beslut för etapp 4:s skyddsräcken.

### 17.5 Underlag och tröskelvärden

- Under `WEIGHT_MIN_RACES_REPORT` (40) lopp redovisas bara antalet; ingen anpassning görs.
- Under `MIN_RACES_FOR_TUNING` (300, avsnitt 5) märks hela rapporten **preliminär**.
- Lopp redovisas per `parameter_version` och `code_version`; blandas flera versioner varnar rapporten (regimerna i avsnitt 3b). `--parameter-version` begränsar analysen till en uppsättning.

### 17.6 Filer

`learning/analysis/weight_analysis.py` (generell kärna: anpassning, walk-forward, bootstrap, mervärdestest – känner inte till trav), `learning/analysis/weight_report.py` (textrapport), `learning/trav/weight_features.py` (vilka mått som är signaler, koppling till parametrar), `learning/trav/settings.py` (trösklar `WEIGHT_MIN_RACES_REPORT`, `WEIGHT_RIDGE`, `WEIGHT_BOOTSTRAP`; läggs dit av `script/patch_weight_analysis.py`), `script/learning_weight_report.py` (CLI, läser bara).

Nästa: etapp 4 (guard, adjuster, rollback, reset) använder förslaget från denna rapport som kandidat – först när underlaget räcker.

### 17.7 Test och körtid

Testad på syntetiska lopp med känd sanning: kända vikter återfinns inom konfidensintervallen, anpassade vikter slår nuvarande bara när nuvarande är fel (ingen falsk förbättring när nuvarande modell är sanningen), expertprovet ger inga fler falsklarm än nominella 5 % på ren brusdata, och en körning mot en syntetisk databas går hela vägen (bortfall, flera versioner, preliminärmärkning, JSON-rapport). Körtiden är några sekunder för hundratals lopp; antalet bootstrap-omtagningar styrs av `--boot` (förval 60).

## 18. Etapp 4 – automatisk justering med skyddsräcken (byggd, avstängd som standard)

Etapp 4 genomför avsnitt 4–5. Den **levereras avstängd** (`auto_enabled = 0`) och ändrar inget förrän användaren slår på den. Även påslagen gör den ingenting förrän alla skyddsräcken är uppfyllda. Med `--dry-run` visas vad som skulle hända utan att något skrivs.

### 18.1 Principer

- **Delpoängen är oberoende av vikterna.** Eftersom varje delpoäng loggas (avsnitt 16.4) går nuvarande modells poäng och en kandidats poäng att räkna om på samma lopp: `poäng = Σ effektiv_vikt_j · delpoäng_j`. Därför kan lopp gjorda med olika parameteruppsättningar användas tillsammans. Det som får blanda sig är inte vikterna utan *signalernas definition* – det är regimen i avsnitt 3b (`settings.REGIMES`): bara lopp från aktuell regim används.
- **Oberoende verifiering.** `adjuster` bygger kandidaten; `guard` kontrollerar den separat och får veto. Ingen kandidat antas om någon kontroll faller.
- **Ändrar bara det som är beslutat:** Crowd-, Chaos- och Score-vikterna (avsnitt 16.2). `crowd.expert` rörs inte (expertindexet är observe-only, se 006). Allt annat – garderingsparametrar, KAMT v2-koefficienter – är senare, separata beslut.

### 18.2 Flödet (`run`)

1. **Avstängd?** Då avslutas körningen (utom `--dry-run`).
2. **Underlag:** avgjorda KAMT v1-lopp i aktuell regim med alla delpoäng (som i avsnitt 17).
3. **Skyddsräcke 1 och 7 (data och avkylning):** minst `TUNING_MIN_RACES` (300) lopp totalt och minst `TUNING_MIN_NEW_RACES` (100) lopp *efter* senaste antagna justering. Faller något: ingen kandidat byggs.
4. **Kandidat (skyddsräcke 2, 4, 5):** loppen delas i tid, äldsta 70 % tränar. Conditional logit på träningsdelen ger föreslagna vikter (samma mappning som avsnitt 17.3). Sedan: *dämpning* `ny = gammal + η·(föreslagen − gammal)` med η = `TUNING_DAMPING` (0,2), *stegtak* ±`TUNING_STEP_CAP` (10 %) relativt gällande värde, och *totalt tak* ±`TUNING_TOTAL_CAP` (50 %) relativt baseline. `score.crowd + score.chaos` hålls lika med 1 och båda följer takten. Beräkningen sker alltid på hela historiken i batch, aldrig på senaste loppet.
5. **Skyddsräcke 3 och 6 (statistisk signal och walk-forward):** båda prövas på de nyaste 30 %, som varken förslaget eller kandidaten sett. Både nuvarande och prövad uppsättning omvandlas med en temperatur som anpassas på träningsdelen.
   - **Riktningen (räcke 3):** det fullständiga, odämpade förslaget mot nuvarande. Skillnaden i log-loss per lopp får ett bootstrap-intervall som måste ligga **helt under 0**.
   - **Steget (räcke 6):** den dämpade, tak-begränsade kandidaten mot nuvarande. Den måste vara **bättre** (negativ skillnad) på de osedda loppen.
   - *Avvikelse från den bokstavliga läsningen i avsnitt 5, med skäl:* att kräva statistisk signifikans för varje enskilt steg på högst 10 % går inte – ett så litet steg ryms alltid inom bruset, så ingenting skulle någonsin antas. Signifikansen krävs därför av den riktning data stödjer; steget (en liten del på vägen dit) måste bara faktiskt vara bättre på osedda lopp. Båda måste gälla. Annars sparas kandidaten som `rejected`.
6. **Guard** kontrollerar punkterna ovan oberoende (inklusive att taken och summan faktiskt håller). Allt godkänt: kandidaten sparas som ny version med status `active`, förälder = tidigare aktiv version, med orsak och underlag (`evidence`). `app.py` läser den vid nästa spelanalys (provider.refresh).
7. **Skyddsräcke 10 (spårbarhet):** varje beslut (`adopted`, `rejected`, `rolled_back`, `reset`, `enabled`, `disabled`) skrivs till `tuning_log` med skäl och underlag.

### 18.3 Återrullning (skyddsräcke 8)

`monitor` jämför den aktiva versionen mot sin förälder över lopp som gjorts *med* den aktiva versionen (`parameter_version`). Kontrafaktisk poäng för föräldern räknas om från delpoängen på samma lopp, så jämförelsen är parvis. Först när minst `ROLLBACK_MIN_RACES` (50) lopp finns beslutas något, och högst de första `ROLLBACK_WINDOW` (100) räknas. Är den aktiva versionen **klart sämre** (hela intervallet för skillnaden i log-loss över 0) sätts den till `rolled_back` och föräldern blir åter aktiv. Annars lämnas den.

### 18.4 Manuell reset (skyddsräcke 9)

`reset` (till baseline) eller `reset --to <version>` återställer aktiv uppsättning, sätter ersatta versioner till `rolled_back`, och **stänger av** automatiken tills användaren slår på den igen med `enable`. En webbknapp är inte byggd; kommandona är den manuella vägen.

### 18.5 Lagring

Tabell `tuning_state (key, value, updated_at)` (nyckeln `auto_enabled`) och `tuning_log (id, logged_at, action, version, reason, evidence)`, båda i Knowledge Base via `DatabaseManager`. Parametrar och trösklar i `learning/trav/settings.py`.

### 18.6 Filer

`learning/tuning/adjuster.py` (kandidat: dämpning, tak, summor), `guard.py` (kontroller), `rollback_monitor.py` (beslutsregel), `tuning_log.py` (tillstånd och logg), `tuner.py` (flödet, generellt via adapter), `learning/trav/tuning_adapter.py` (travspecifikt), `script/learning_tuning.py` (`status`, `run`, `monitor`, `enable`, `disable`, `reset`, `log`).

### 18.7 Medvetna begränsningar

- Justeringen kan startas för hand (`run`). Koppling till Learning Engines utvärdering beskrivs i 18.9.
- Underlaget idag räcker inte: delpoängen loggas sedan 2026-10-12, så 300 lopp tar några veckor. Fram till dess säger `run` att det är för lite data.
- Poäng räknas om utan expert och med neutralt 50 för saknad trend – samma förenkling som i avsnitt 17.

### 18.8 Test

Testad på syntetiska lopp och mot en syntetisk databas via kommandoraden. Varje skyddsräcke har ett eget prov som fäller en manipulerad kandidat (stegtak, totalt tak, dämpning, summor, avgränsning, meningsfull ändring, data, avkylning, signal, walk-forward). Hela kedjan: avstängd ändrar inget; torrkörning skriver inget; påslagen antar ett dämpat steg på högst 10 % när riktningen är klart bättre; ny justering direkt efteråt stoppas av avkylningen; för lite data ger inget; när nuvarande modell är sanningen antogs ingen justering i 24 av 24 körningar; återrullning sker när en ny version är klart sämre och inte annars; `reset` återställer och pausar automatiken.

### 18.9 Koppling till Learning Engines utvärdering (arkitekturbeslut)

**Mål.** Efter att en utvärdering är klar ska systemet självt pröva återrullning och ny justering, men bara om automatiken är påslagen (`auto_enabled`, avstängd som standard). Då får Learning Engine ett riktigt kretslopp: prognos → utfall → ny utvärdering → eventuellt ny parameteruppsättning → nästa prognos (via `ParameterProvider.refresh()` som redan körs före varje analys).

**Var.** Anropet sitter sist i `LearningEngine.evaluate()`, efter att observationerna är loggade och utvärderingen sparad. Learning Engine känner bara till en enda funktion, `after_evaluation()`, inte till Tuner, adapter eller parametrar. Den som kallar `evaluate` (appen, `reevaluate_*`, CLI) behöver inte ändras.

**Ansvar.**
- `learning/tuning/auto_runner.py` (generell): `AutoRunner(tuner_factory)`. `after_evaluation()` gör, i ordning: (1) om automatiken är av, returnera direkt (en enda läsning); (2) ta ett lås – körs redan en justering hoppas denna över; (3) kör `monitor` och därefter `run` i en bakgrundstråd som inte är daemon (hinner alltså slutföra vid avslut, så en justering aldrig avbryts halvvägs); (4) fånga alla fel och skriv dem som `error` i justeringsloggen.
- `learning/trav/tuning_factory.py` (travspecifikt): bygger Tuner med trav-adaptern. Används av både `AutoRunner` och `script/learning_tuning.py`, så ingen kod dupliceras.
- `learning/trav/auto_hook.py` (travspecifikt): tillhandahåller `after_evaluation()` med trav-fabriken inkopplad, så att `services/learning_engine.py` bara importerar en funktion.

**Garantier.**
- Ett fel i justeringen kan aldrig stoppa eller ändra utvärderingen eller loggningen av observationer (egen felfångst, separat tråd).
- Avstängd automatik ger exakt samma beteende som före kopplingen.
- Alla skyddsräcken i 18.2–18.4 gäller oförändrade; kopplingen lägger bara till *när* de prövas. Avkylning och krav på nya lopp gör att täta utvärderingar (t.ex. `reevaluate_all`) inte ger fler justeringar, bara fler snabbt avvisade prövningar. Dubbla körningar hindras av låset.
- `monitor` körs före `run`, så en dålig version rullas tillbaka innan en ny justering prövas ovanpå den.

**Begränsning.** Ingen schemaläggning och ingen webbknapp (separata beslut). Körtiden för en justering på 420 syntetiska lopp var under en sekund.

Test av kopplingen: avstängd gör ingenting; påslagen antar en dämpad version i bakgrunden; direkt ny utvärdering stoppas av avkylningen; en tuner som kraschar loggas som `error` utan att något når anroparen; en pågående körning släpper inte in en andra; `LearningEngine.evaluate` anropar kopplingen. Anslutningar byggs i den egna tråden (SQLite delas inte mellan trådar).
