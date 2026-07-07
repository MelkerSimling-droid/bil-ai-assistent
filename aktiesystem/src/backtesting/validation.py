"""Out-of-sample-utvärdering: skydd mot overfitting.

Idén: dela historiken i en in-sample-period (där man typiskt trimmat
parametrarna) och en efterföljande out-of-sample-period som strategin
"aldrig sett". Om resultatet försämras kraftigt out-of-sample är det en
stark signal att strategin är anpassad till brus snarare än en robust
egenskap hos marknaden.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.backtesting.costs import CostModel
from src.backtesting.engine import BacktestEngine, BacktestResult
from src.backtesting.strategy import Strategy

#: Sharpe out-of-sample under denna andel av in-sample ⇒ varning.
_DEGRADATION_THRESHOLD = 0.5


@dataclass
class SplitBacktestResult:
    """Resultat av ett tudelat backtest."""

    in_sample: BacktestResult
    out_of_sample: BacktestResult
    split_date: pd.Timestamp
    warnings: list[str]


def split_prices(
    prices: dict[str, pd.DataFrame], in_sample_fraction: float = 0.7
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], pd.Timestamp]:
    """Delar prisdata i en tidig och en sen period vid ett gemensamt datum.

    Brytdatumet väljs ur den gemensamma handelskalendern (union av alla
    tickers datum) så att båda perioderna är sammanhängande i tid — ingen
    överlappning och inget datum ingår i båda.

    Args:
        prices: Per ticker: OHLCV-frame med DatetimeIndex.
        in_sample_fraction: Andel av kalendern som blir in-sample (0.5–0.9).

    Returns:
        (in_sample-priser, out_of_sample-priser, första out-of-sample-datumet).

    Raises:
        ValueError: Vid ogiltig andel eller för kort historik för en
            meningsfull delning.
    """
    if not 0.5 <= in_sample_fraction <= 0.9:
        raise ValueError(
            f"in_sample_fraction ska vara mellan 0.5 och 0.9, fick {in_sample_fraction}."
        )
    calendar = sorted(set().union(*(frame.index for frame in prices.values())))
    if len(calendar) < 120:
        raise ValueError(
            f"Minst 120 handelsdagar krävs för en meningsfull delning, fick {len(calendar)}."
        )
    split_index = int(len(calendar) * in_sample_fraction)
    split_date = calendar[split_index]
    in_sample = {ticker: frame.loc[: calendar[split_index - 1]] for ticker, frame in prices.items()}
    out_of_sample = {ticker: frame.loc[split_date:] for ticker, frame in prices.items()}
    return in_sample, out_of_sample, split_date


def run_split_backtest(
    prices: dict[str, pd.DataFrame],
    strategy: Strategy,
    start_capital: float,
    cost_model: CostModel,
    benchmark_close: pd.Series | None = None,
    risk_free_rate: float = 0.02,
    in_sample_fraction: float = 0.7,
) -> SplitBacktestResult:
    """Kör samma strategi på in-sample- och out-of-sample-perioden separat.

    Båda körningarna startar med samma kapital så att nyckeltalen är
    jämförbara. Out-of-sample-perioden är alltid den SENARE — att testa
    "framåt i tiden" är poängen.

    Returns:
        SplitBacktestResult med båda resultaten och varningar om
        prestandan försämras kraftigt out-of-sample.
    """
    early, late, split_date = split_prices(prices, in_sample_fraction)

    def bench_slice(period: dict[str, pd.DataFrame]) -> pd.Series | None:
        if benchmark_close is None:
            return None
        calendar = sorted(set().union(*(frame.index for frame in period.values())))
        return benchmark_close.loc[calendar[0] : calendar[-1]]

    result_in = BacktestEngine(
        early, strategy, start_capital, cost_model, bench_slice(early), risk_free_rate
    ).run()
    result_out = BacktestEngine(
        late, strategy, start_capital, cost_model, bench_slice(late), risk_free_rate
    ).run()

    warnings = _compare(result_in, result_out)
    return SplitBacktestResult(result_in, result_out, split_date, warnings)


def _compare(result_in: BacktestResult, result_out: BacktestResult) -> list[str]:
    """Varningar när out-of-sample tydligt underpresterar in-sample."""
    warnings: list[str] = []
    sharpe_in = result_in.metrics.get("sharpe", 0.0)
    sharpe_out = result_out.metrics.get("sharpe", 0.0)
    if sharpe_in > 0 and sharpe_out < sharpe_in * _DEGRADATION_THRESHOLD:
        warnings.append(
            f"Sharpe föll från {sharpe_in:.2f} (in-sample) till {sharpe_out:.2f} "
            "(out-of-sample) — ett typiskt tecken på att parametrarna är "
            "anpassade till historiskt brus (overfitting)."
        )
    if (
        result_in.metrics.get("total_avkastning", 0.0)
        > 0
        > result_out.metrics.get("total_avkastning", 0.0)
    ):
        warnings.append(
            "Strategin var lönsam in-sample men förlorade pengar out-of-sample. "
            "Betrakta in-sample-resultatet med stor skepsis."
        )
    if not warnings:
        warnings.append(
            "Ingen kraftig försämring out-of-sample upptäcktes. Det utesluter inte "
            "overfitting — men det är ett bättre tecken än motsatsen."
        )
    return warnings
