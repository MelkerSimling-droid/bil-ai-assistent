# Antaganden

Beslut jag fattat där specifikationen lämnade utrymme. Allt här går att
ändra — filen finns för att inget ska vara dolt.

## Miljö och verktyg

1. **Projektets placering:** `aktiesystem/` ligger som fristående mapp i
   `bil-ai-assistent/` (där sessionen startades). Projektet har inga beroenden
   till mappen omkring och kan flyttas var som helst med `mv`.
2. **Python:** datorn hade bara Python 3.9, spec kräver 3.11+. Jag installerade
   [uv](https://docs.astral.sh/uv/) (i `~/.local/bin`) som i sin tur hanterar
   Python 3.12.13 i projektets `.venv`.
3. **Egna indikatorer i stället för pandas-ta:** biblioteket har kända
   kompatibilitetsproblem med numpy ≥ 2. Egna implementationer valideras mot
   handräknade referensvärden i `tests/test_indicators.py` (spec:en öppnade
   uttryckligen för detta).
4. **Egen portföljoptimering i stället för PyPortfolioOpt:** samma
   Markowitz-matematik, men via `scipy.optimize` — slipper det tunga
   cvxpy-beroendet.

## Data

5. **Kurser är utdelningsjusterade** (`auto_adjust=True` i yfinance). Backtestens
   avkastning är därmed ungefär totalavkastning. Benchmarkindexet `^OMX` är dock
   ett **prisindex utan utdelningar**, så indexjämförelsen är något generös mot
   strategin. Byt benchmark i `config.yaml` om du vill ha annan bas.
6. **Cachens färskhet:** 12 timmar (konfigurerbart). Vid API-fel används cachad
   data med tydlig loggvarning; utan cache visas "data saknas" i UI.
7. **Intradagsdata** stöds för intervallen 1h (ca 2 års historik hos Yahoo)
   och 15m (ca 60 dagar). Datat är fördröjt (inte realtid), cachas i en egen
   tabell med 1 timmes färskhet, och tidsstämplarna är i börsens lokala tid.
   Yahoo-index på intradagsnivå är opålitliga, så intradagsbacktester görs
   utan indexjämförelse. Prestanda: strategier deklarerar `max_lookback` så
   motorn bara skickar den historiksvans indikatorn behöver (exakt för SMA;
   för RSI/Bollinger med hysteres ett 20×period-fönster, vilket i sällsynta
   fall — position öppen längre än hela fönstret utan att säljnivån nåtts —
   kan ge annat tillstånd än full historik). Verifierat: 6 432 timbarer på
   ~16 s med identiskt resultat som full-historik-körningen.
8. **Standardbevakningslista:** 4 svenska + 2 amerikanska aktier som exempel —
   byt fritt under Inställningar.

## Backtestmotorn

9. **Endast långa positioner** (signal 0/1, ingen blankning) i v1.
10. **Likaviktad allokering:** målvikt 1/N per ticker i universumet; köp sker
    bara om kassan räcker (ingen belåning); sälj stänger hela innehavet.
11. **Exekvering:** signal dag T ⇒ affär på öppningskursen dag T+1 (± slippage).
    Saknas bar dag T+1 ligger ordern kvar till nästa handelsdag.
12. **Courtagemodell (standard):** `max(1 kr, 0.069 % × belopp)` ≈ svensk
    nätmäklares miniklass, plus slippage 0,05 % per affär. Allt i `config.yaml`.
13. **Öppna positioner vid periodens slut** ingår i equity men inte i win
    rate/snittvinst — det varnas för detta i resultatet.
14. **Out-of-sample-utvärdering:** valfri 70/30-delning av historiken där
    strategin körs separat på båda perioderna med samma startkapital.
    Tröskeln "Sharpe out-of-sample < 50 % av in-sample ⇒ varning" är en
    tumregel, inget statistiskt test. Delningen kräver minst 120 handelsdagar.
    Alternativt finns rullande fönster: fyra lika långa delperioder körs var
    för sig (minst 60 handelsdagar per fönster) med konsekvensvarningar.
15. **Exponering** i nyckeltalen = andel handelsdagar med minst en öppen
    position. Redovisas för att avkastning inte ska jämföras rakt av med ett
    alltid-investerat index när strategin mest ligger i kassa.
16. **Körningsloggning:** varje enskild backtestkörning i dashboarden sparas
    automatiskt som JSON under `data/processed/backtests/` (tidsstämpel,
    strategi, parametrar, nyckeltal, equity-kurva) för reproducerbarhet.

## Risk, DCF, sentiment

17. **Riskfri ränta:** 2 % årligen som standard (Sharpe/Sortino/frontier).
18. **VaR:** historisk simulering, kräver minst 30 observationer; ingen
    parametrisk modell.
19. **DCF:** tvåstegsmodell (prognosår + Gordon-terminal). Kräver positivt fritt
    kassaflöde; saknas nettoskuldsdata antas 0 **med synlig flaggning i UI**.
20. **Sentiment:** VADER är engelskspråkigt — svenska rubriker poängsätts
    opålitligt. Detta står som varning direkt i sentimentvyn. Nyheter hämtas
    via yfinance (ingen nyckel); rubriker utan datum grupperas som
    "okänt datum" i stället för att ges ett gissat datum.

## Övrigt

21. **Valutakonvertering i översikten:** innehav räknas om till basvalutan
    (`base_currency` i config.yaml, standard SEK) med senaste växelkurs från
    Yahoo (t.ex. USDSEK=X); kursen redovisas i tabellen. Kan valuta eller
    växelkurs inte hämtas **exkluderas innehavet ur summorna** med en synlig
    varning — det gissas aldrig in. Riskmåtten (volatilitet/VaR/korrelation)
    beräknas på avkastningar i lokal valuta; valutarörelser ingår inte (står i UI).
22. **Portföljinnehav** anges i `config.yaml` under `holdings:` (exempelvärden
    inlagda) — det finns ingen transaktionshistorik/databas för egna affärer i v1.
23. **Dashboardporten** är 8503 (vald för att inte krocka med annat på datorn).
24. **Marknadsbevakningen** skickar notiser om indikatorhändelser — ALDRIG
    "köp"/"sälj" (spec-princip 2). Reglerna triggar bara på nya korsningar/
    händelser i senaste baren, och varje larm-id (ticker + regel + dag)
    notifieras max en gång (SQLite-dubblettskydd). Notiskanal: macOS via
    osascript; fler kanaler kan pluggas in via Notifier-interfacet.
    Sentimentlarm kräver minst 3 rubriker. Schemaläggningen (LaunchAgent,
    var 30:e minut) installeras medvetet INTE automatiskt — den kräver två
    manuella kommandon (se README) eftersom det är en beständig systemändring.
