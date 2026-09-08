# Chaos Insight

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
