# Aktiesystem — analys- och beslutsstöd

Ett lokalt, modulärt aktieanalyssystem i Python: datainhämtning med cachning,
teknisk och fundamental analys, nyhetssentiment, riskhantering, event-driven
backtesting utan lookahead bias, portföljoptimering och ett Streamlit-dashboard.

> ## ⚠️ Viktigt — läs först
> Det här verktyget är byggt för **utbildnings- och analyssyfte** och utgör
> **inte finansiell rådgivning**. Det presenterar historisk data och beräknade
> indikatorer — det förutsäger inte framtiden. **Historisk avkastning i
> backtester är ingen garanti för framtida resultat.** Systemet lägger aldrig
> ordrar och ger aldrig köp-/säljrekommendationer. Du ansvarar själv för alla
> investeringsbeslut.

## Installation

Kräver Python 3.11+ (projektet är byggt och testat med 3.12 via
[uv](https://docs.astral.sh/uv/)).

```bash
cd aktiesystem

# Med uv (rekommenderas):
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# ... eller med vanlig python 3.11+:
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Valfritt: kopiera `config/.env.example` till `.env` och fyll i API-nycklar.
**Ingen nyckel behövs för basdrift** — kursdata kommer från Yahoo Finance via
yfinance. `.env` är gitignorad och nycklar hårdkodas aldrig i koden.

## Starta dashboarden

```bash
.venv/bin/python -m streamlit run dashboard/app.py
```

Öppna http://localhost:8501 (porten som streamlit skriver ut). Sex sidor:

| Sida | Innehåll |
|---|---|
| Översikt | Portföljvärde i basvalutan (automatisk växelkursomräkning), dagens förändring, volatilitet, max drawdown, VaR, korrelationer, larmhistorik |
| Morgonkoll | Hela bevakningslistan i en sorterbar tabell: trend, RSI, MACD, avstånd till 52-veckorsnivåer, volatilitet — allt i klartext med förklaringar |
| Aktieanalys | Kursgraf med SMA/Bollinger/RSI/MACD, intradagsvy (1h/15m) med VWAP och volym, nyckeltal, DCF med känslighetstabell, sentiment, position sizing |
| Screening | Filtrera bevakningslistan på P/E, skuldsättning m.m. — saknad data redovisas separat |
| Backtesting | Fyra strategier (SMA-korsning, RSI mean reversion, Bollinger-reversion, tidsseriemomentum) på dagsdata eller intradagsbarer (1h/15m) med courtage & slippage; strategijämförelse mot köp & behåll; robusthetsutvärdering via 70/30-delning eller rullande fönster; exponeringsmått; varje körning sparas som JSON för spårbarhet |
| Portföljoptimering | Efficient frontier, referensportföljer, rebalanseringsförslag |
| Inställningar | Bevakningslista, datasynk, riskparametrar, API-nyckelstatus |

## Marknadsbevakning med notiser

Systemet kan bevaka din bevakningslista och skicka **macOS-notiser** när ett
villkor inträffar — t.ex. RSI korsar under 30, kursen korsar SMA 200, en
dagsrörelse större än ±4 %, eller starkt negativt/positivt nyhetssentiment.

> **Viktigt:** ett larm är en *indikatorobservation* ("RSI gick under 30"),
> aldrig en köp- eller säljrekommendation. Systemet vet inte vad som händer
> imorgon — beslutet är alltid ditt.

```bash
# Kör en bevakningsrunda manuellt:
.venv/bin/python -m src.monitoring.monitor
```

Regler och nivåer ställs in under `monitoring:` i `config/config.yaml`.
Varje larm notifieras bara en gång (dubblettskydd i SQLite) och hela
historiken visas på dashboardens översiktssida.

**Schemalägg var 30:e minut** (macOS LaunchAgent, kräver ditt godkännande):

```bash
cp scripts/se.aktiesystem.monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/se.aktiesystem.monitor.plist
```

Stäng av med `launchctl unload ~/Library/LaunchAgents/se.aktiesystem.monitor.plist`.

## Konfiguration

Allt styrs från [`config/config.yaml`](config/config.yaml): bevakningslista,
innehav, benchmarkindex, courtagemodell, riskparametrar. Kommentarerna i filen
förklarar varje fält.

## Köra testerna

```bash
.venv/bin/python -m pytest        # hela sviten
.venv/bin/python -m pytest tests/test_backtesting.py -v   # bara motorn
```

Testerna körs helt offline (fejk-adapter + syntetisk data) och täcker
indikatorberäkningar (mot handräknade referensvärden), cache/fallback-logik,
riskmått, DCF, portföljoptimering, sentiment och — viktigast — att
backtestmotorn **aldrig läcker framtida data** in i en signal.

## Arkitektur

```
aktiesystem/
├── config/            config.yaml + .env.example
├── data/raw/          SQLite-cache med sync-logg (tidsstämpel/källa/parametrar)
├── src/
│   ├── data_ingestion/  adapter-mönster (yfinance nu; fler källor pluggas in)
│   ├── indicators/      SMA, EMA, RSI, MACD, Bollinger, ATR, OBV
│   ├── fundamentals/    nyckeltal, screening, DCF
│   ├── sentiment/       VADER på nyhetsrubriker (grov approximation!)
│   ├── risk/            position sizing, volatilitet, korrelation, VaR, drawdown
│   ├── backtesting/     event-driven motor — läs src/backtesting/README.md
│   ├── portfolio/       efficient frontier (Markowitz), rebalansering
│   └── utils/           config, loggning, retry
├── dashboard/           Streamlit-app (en vy per fil)
├── tests/               pytest-svit, körs offline
└── logs/                roterande loggfiler
```

Designprinciper (se även [ANTAGANDEN.md](ANTAGANDEN.md)):

* **Inga påhittade data.** API-fel ⇒ cachad data med varning, eller "data
  saknas" i UI. Saknade nyckeltal förblir tomma.
* **Inga rekommendationer.** All text beskriver vad indikatorer visar.
* **Inget lookahead.** Signal dag T handlas på öppningen dag T+1; motorn ger
  strategin en dataslice som slutar "nu". Verifierat med dedikerade tester.
* **Reproducerbarhet.** Varje datahämtning loggas med tidsstämpel, källa och
  parametrar i cachens `sync_log`-tabell.
* **Ingen automatisk handel.** Det finns ingen orderläggningskod, avsiktligt.

## Kodkvalitet

```bash
.venv/bin/python -m black src tests dashboard    # formatering
.venv/bin/python -m ruff check src tests dashboard
```

## Vanliga frågor

* **"Data saknas" för en ticker?** Kontrollera stavningen i Yahoo-format
  (svenska aktier: `VOLV-B.ST`). Se `logs/aktiesystem.log` för felet.
* **Byta datakälla?** Implementera `MarketDataAdapter` i
  `src/data_ingestion/` och byt i `MarketDataService.from_config`.
* **Postgres i stället för SQLite?** All SQL bor i
  `src/data_ingestion/cache.py` — byt den klassen, resten är opåverkat.
