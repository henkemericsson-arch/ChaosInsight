# Chaos Insight

## Unreleased

- Learning Engine etapp 1b: rapport för spik/lås-urval, kaosvärde och täckning mot marknaden (script/learning_leg_report.py).
- Strukna hästar filtreras bort redan vid parsning (RaceParser) och odds 0 behandlas som struken i SystemGenerator.
- Lås väljs nu som de två främsta favoriterna enligt odds, rankade på summan av deras Total Score (samma princip som spikar).
- KAMT v2: hästar utan sannolikhet från RaceAnalyzer tappas inte längre, de får ett lågt standardvärde så att favoriter alltid kan bli spik, lås eller gardering.
- Expertmodul: ChaosInsight hämtar själv dagens expertartiklar från källorna i config/expert_sources.py (robots.txt respekteras), tolkar texten med en egen regelbaserad tolkare (ingen extern AI-tjänst) och sparar tipsen i Knowledge Base (tabellerna expert_tips och expert_articles). Insamlingen startas automatiskt i bakgrunden när ett spel öppnas.
- ExpertAnalyzer (Analysis Engine) räknar ut expert_index per häst som en vanlig parameter. Indexet går i observe-only-läge (expert_index_obs, vikt 0) tills Learning Engine visat att det tillför något.
- Learning Engine etapp 2 steg 1: alla hästmått (metrics_json) och kodversion (code_version) loggas nu i prediktioner och observationer, så att varje parameter kan utvärderas i efterhand.
- KAMT v2: ShadowHorse har nu samma metrics-attribut som Horse så att skuggsystemet kan loggas med hästmått.
- Utredning: hästnivåns marknadsresidual testad på 71 201 lopp, ingen signal, parametern byggdes inte (005_Learning_Engine_Design.md §14).
- Dokumentation: 005_Learning_Engine_Design.md (§14–15) och 006_Expert_Module_Design.md.
- Parameterlager: Crowd-, Chaos- och Score-vikterna läses nu från en versionerad parameteruppsättning (tabellen parameter_sets, ParameterStore/ParameterProvider i learning/tuning/, baseline i learning/trav/parameter_schema.py) i stället för klasskonstanter. Version 0 (baseline) är dagens värden och oföränderlig; Total Score är identisk med tidigare. Grunden för Learning Engine etapp 4.
- parameter_version sparas i prediktionsfiler och observationer (ny kolumn i observations).
- Delpoäng per häst (odds, streck, trend, startspår, kusk, form, distans, bana, galopp, tempo, datatäckning) sparas nu som mått och hamnar i metrics_json, vilket är förutsättningen för viktanalysen (etapp 2a). Äldre lopp saknar dem.
- script/learning_parameters.py visar aktiv parameteruppsättning och alla versioner.
- Dokumentation: 005_Learning_Engine_Design.md avsnitt 16.
- Viktanalys (etapp 2a): conditional logit på loggade delpoäng, walk-forward mot nuvarande Total Score, koefficienter med bootstrap-KI, förslag i parametrarnas termer och prov av expertindexets mervärde (script/learning_weight_report.py, learning/analysis/weight_analysis.py, learning/trav/weight_features.py). Läser bara; ändrar inget i systemet.

## Version 0.5.1

- Automatisk justering (etapp 4): dämpad, skyddad parameterjustering med återrullning (learning/tuning), AV som standard. Se 005 §18.

## Version 0.5.0
**Status:** Klar

### Nytt
- **KAMT v2**: helt ny parallell analysarkitektur baserad på Monte Carlo-simulering istället för viktad poängsumma. Egen baslinjeberäkning per häst (Nivå 1), fyra kopplingsmatriser A–D plus en separat korstabell-mekanism (Nivå 2), och en generell Monte Carlo-motor (Nivå 3). Körs i skuggläge parallellt med KAMT v1 i `/resultat`, sparas och utvärderas som riktiga system, med en egen jämförelsesida (`/kamt-jamforelse`) som visar lopp-för-lopp hur ofta KAMT v1 och KAMT v2 träffar olika lopp.
- **SystemGenerator ombyggd i flera steg**: risknivån styr numera favorit/skräll-fördelningen (kalibrerad till Låg 50 % / Mellan 30 % / Hög 10 %) istället för garderingens bredd. Garderingsbredden skalar istället kontinuerligt med loppets kaosvärde. Ett nytt budgetsteg breddar garderingen mot budgettaket när utrymme finns kvar, istället för att lämna budget outnyttjad. Spik och lås väljs numera genom att jämföra alla lopps marknadsfavoriter mot varandra efter Total Score — favoriten garanteras alltid vara med i spik och lås, inte bara i vanlig gardering.
- **Learning Engine**: hanterar nu ATG:s platsangivelse som fallback när `finishOrder` saknas, och tillämpar automatisk reservsubstitution när en markerad häst blir struken (ersätts av nästa lediga häst i ATG:s reservordning, precis som ATG själv gör). Rensar automatiskt bort inaktuella observationsrader vid varje omvärdering.
- **Trådsäkerhet**: `DatabaseManager` och `HistoricalStatsProvider` använder nu `threading.local()` istället för globala singletons, vilket löste återkommande krascher (`SQLite objects created in a thread...`) vid samtidig bakgrundsbackfill och webbtrafik.
- All historikdata migrerad till SQLite (`backfill_starts`, `observations`, `kamt_v2_forecasts`), med backfill utökad till 2021-10-01.
- Bana+distans-fallback: lopp där ingen häst har egen tillräcklig historik kan nu ändå analyseras via ett grövre bana/distans-genomsnitt, istället för att hoppas över helt.
- Fixade en `race_number`-kollisionsbugg som orsakade felaktig matchning i V86 Xpress-spel med flera banor.
- Fixade ett felaktigt läst fält (`out` istället för `scratched`) i resultattolkningen som gav felaktig strukningsstatus i historikdatan.

### Testat
- Reservsubstitution och platsfallback verifierat mot verklig ATG-data (inklusive dubbla samtidiga strukningar i samma lopp).
- SystemGenerators nya spik/lås-princip, favoritgolv och budgetbreddning testat mot flera scenarier, inklusive det verkliga fallet som avslöjade att en marknadsfavorit kunde missas i spikval.
- Trådsäkerhetsfixarna verifierat med simulerade samtidiga trådar.
- Bana+distans-fallbacken verifierat både när den räddar ett annars uteslutet lopp och när den korrekt fortsätter utesluta lopp helt utan data.

### Kända begränsningar
- Galoppbanor (t.ex. Bro Park) filtreras ännu inte bort från insamling/analys, trots att plattformen är avsedd enbart för trav — identifierat men inte åtgärdat.
- KAMT v2:s matriskoefficienter är fortfarande overifierade och kalibreras inte automatiskt utifrån utfall.
- Arkitekturmigreringen mot en renodlad lagerindelning (`003_Restructuring_Plan.md`) är påbörjad men långt ifrån klar — `app.py` innehåller fortfarande spelspecifik logik.

### Nästa version (v0.6.0)
- Filtrera bort galoppbanor från backfill och livehämtning.
- Påbörja Learning Engine-driven kalibrering av KAMT v2:s matriskoefficienter.
- Fortsätta arkitekturmigreringen: flytta `race_analyzer.py`, `trav_race_simulator.py` och KAMT v2-modulerna till `modules/trav/`.

## Version 0.1.0
**Status:** Klar

### Nytt
- Projektstruktur skapad.
- Core Engine implementerad.
- Logger implementerad.
- Första körbara versionen av Chaos Insight.

### Testat
- Programmet startar.
- Core Engine initieras.
- Logger skriver till terminal.
- Loggfil (`logs/chaosinsight.log`) skapas automatiskt.
