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
    periods_per_year: float = 252.0,
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
        early,
        strategy,
        start_capital,
        cost_model,
        bench_slice(early),
        risk_free_rate,
        periods_per_year=periods_per_year,
    ).run()
    result_out = BacktestEngine(
        late,
        strategy,
        start_capital,
        cost_model,
        bench_slice(late),
        risk_free_rate,
        periods_per_year=periods_per_year,
    ).run()

    warnings = _compare(result_in, result_out)
    return SplitBacktestResult(result_in, result_out, split_date, warnings)


@dataclass
class WindowResult:
    """Resultatet av en delperiod i den rullande utvärderingen."""

    start: pd.Timestamp
    end: pd.Timestamp
    result: BacktestResult


def rolling_window_evaluation(
    prices: dict[str, pd.DataFrame],
    strategy: Strategy,
    start_capital: float,
    cost_model: CostModel,
    risk_free_rate: float = 0.02,
    n_windows: int = 4,
    periods_per_year: float = 252.0,
) -> tuple[list[WindowResult], list[str]]:
    """Kör strategin separat på N lika långa, icke överlappande delperioder.

    Starkare robusthetstest än en enda delning: en strategi vars resultat
    kommer från en enda lyckad period avslöjas när delperioderna jämförs.
    Varje fönster startar med samma kapital så nyckeltalen är jämförbara.

    Args:
        prices: Per ticker: OHLCV-frame med DatetimeIndex.
        strategy: Strategin som utvärderas (samma parametrar i alla fönster).
        start_capital: Startkapital per fönster.
        cost_model: Courtage-/slippagemodell.
        risk_free_rate: Årlig riskfri ränta för Sharpe/Sortino.
        n_windows: Antal delperioder (2–8).

    Returns:
        (fönsterresultat i kronologisk ordning, varningar om konsekvens).

    Raises:
        ValueError: Vid ogiltigt antal fönster eller för kort historik
            (minst 60 handelsdagar per fönster krävs).
    """
    if not 2 <= n_windows <= 8:
        raise ValueError(f"n_windows ska vara mellan 2 och 8, fick {n_windows}.")
    calendar = sorted(set().union(*(frame.index for frame in prices.values())))
    if len(calendar) < 60 * n_windows:
        raise ValueError(
            f"Minst {60 * n_windows} handelsdagar krävs för {n_windows} fönster, "
            f"fick {len(calendar)}."
        )
    boundaries = [int(len(calendar) * i / n_windows) for i in range(n_windows + 1)]
    windows: list[WindowResult] = []
    for i in range(n_windows):
        start = calendar[boundaries[i]]
        end = calendar[boundaries[i + 1] - 1]
        sliced = {ticker: frame.loc[start:end] for ticker, frame in prices.items()}
        result = BacktestEngine(
            sliced,
            strategy,
            start_capital,
            cost_model,
            None,
            risk_free_rate,
            periods_per_year=periods_per_year,
        ).run()
        windows.append(WindowResult(start, end, result))
    return windows, _consistency_warnings(windows)


def _consistency_warnings(windows: list[WindowResult]) -> list[str]:
    """Varningar när resultatet inte håller över delperioderna."""
    returns = [w.result.metrics.get("total_avkastning", 0.0) for w in windows]
    positive = sum(1 for value in returns if value > 0)
    warnings: list[str] = []
    if positive <= len(windows) / 2:
        warnings.append(
            f"Endast {positive} av {len(windows)} delperioder gav positiv avkastning "
            "— resultatet är inte konsekvent över tid och kan bero på en enskild "
            "gynnsam period."
        )
    best = max(returns)
    if best > 0 and sum(returns) > 0 and best / max(sum(returns), 1e-9) > 0.8 and len(windows) >= 3:
        warnings.append(
            "En enda delperiod står för merparten av totalresultatet — var skeptisk "
            "till att strategin fungerar generellt."
        )
    if not warnings:
        warnings.append(
            f"{positive} av {len(windows)} delperioder gav positiv avkastning. "
            "Konsekvens över delperioder är ett gott tecken, men ingen garanti."
        )
    return warnings


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
