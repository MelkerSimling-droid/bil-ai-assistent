# Backtesting-motorns arkitektur

## Designmål

Motorn är **event-driven**: den går igenom historiken bar för bar (dag för
dag) och simulerar besluten i den ordning de hade kunnat fattas i verkligheten.
Det gör den långsammare än en vektoriserad motor, men strukturellt immun mot
lookahead bias — strategin *kan* inte se framtiden eftersom den bara får en
slice av historiken.

## Tidsmodell — så förhindras lookahead

```
Dag T (efter börsstängning)          Dag T+1 (börsöppning)
─────────────────────────────       ─────────────────────────
1. Equity bokförs på close(T)        4. Köade ordrar exekveras
2. Strategin får data t.o.m. T          på open(T+1) ± slippage
3. Målsignaler blir köade ordrar        + courtage dras från kassan
```

- Strategin anropas med `history[ticker] = frame.loc[:T]` — en kopia av
  datan **till och med dag T**, aldrig längre.
- Ordrar som skapas av signaler dag T exekveras tidigast på **öppningskursen
  dag T+1**. Man kan alltså aldrig handla på samma stängningskurs som
  signalen beräknades på (ett vanligt lookahead-fel i naiva backtester).
- Om en ticker saknar bar dag T+1 (helgdag/handelsstopp) exekveras ordern på
  nästa tillgängliga bar.

Detta verifieras av dedikerade tester i `tests/test_backtesting.py`:
en spionstrategi kontrollerar vid varje anrop att den aldrig ser data efter
"nu", och ett exekveringstest kontrollerar att en signal dag T fylls exakt
på öppningskursen dag T+1.

## Kostnadsmodell

- **Courtage**: `max(minimicourtage, fast avgift + procent × affärsvärde)`
  — parametrarna sätts i `config.yaml` (standard ≈ svensk nätmäklarklass).
- **Slippage**: köp fylls på `open × (1 + slippage)`, sälj på
  `open × (1 − slippage)` — alltid till din nackdel.

## Positionsregler (medvetet enkla i v1)

- Endast långa positioner; signaler är 1 (äga) eller 0 (inte äga).
- Kapitalet delas lika: målvikt = 1/N per ticker i universumet.
- Köp sker bara om kassan räcker (ingen belåning); sälj stänger hela innehavet.

## Utdata

`BacktestResult` innehåller equity-kurva, drawdown-kurva, affärslogg,
nyckeltal (total avkastning, CAGR, Sharpe, Sortino, max drawdown, win rate,
snittvinst/-förlust) samt buy-and-hold-jämförelse mot valt index, plus en
lista `warnings` (t.ex. för få affärer, overfittingrisk) som alltid visas i UI.

## Strategi-interface

Nya strategier ärver `Strategy` och implementerar en enda metod:

```python
class MinStrategi(Strategy):
    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        ...  # returnera {ticker: 0 eller 1}
```

Motorn behöver aldrig ändras för att lägga till en strategi.
