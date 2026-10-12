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

`expert_index` är tomt för att expertdelen ännu inte är byggd, inte på grund av en loggningsbugg. Enligt 003 är experttips en separat komponent (`experttips`, EXPERT-vikt 5 i Crowd) och källorna ska ligga i en egen modul (`config/expert_sources.py`); `app.py` anropar `ExpertAnalyzer.collect_tips()/apply()`. Loggningen ändrar inget där: delmåtten sparas bara om de finns i `horse.metrics`, och inget skrivs för `expert_index` om modulen inte satt det. När expertmodulen byggs behöver den en egen design (källor, insamling, tolkning till per-häst-signal, point-in-time-loggning) – ej beslutad.
