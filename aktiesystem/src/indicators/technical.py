"""Tekniska indikatorer — egna implementationer i pandas/numpy.

Egna implementationer valdes framför pandas-ta (kompatibilitetsproblem med
numpy 2.x) och valideras i tests/test_indicators.py mot handräknade
referensvärden. Alla funktioner returnerar serier/frames alignade med
indata; perioder där indikatorn ännu inte är definierad är NaN — de fylls
aldrig i med gissade värden.
"""

from __future__ import annotations

import pandas as pd


def _require_min_length(series: pd.Series, period: int, name: str) -> None:
    """Kastar ValueError om serien är för kort för indikatorn."""
    if period < 1:
        raise ValueError(f"{name}: period måste vara >= 1, fick {period}.")
    if len(series) < period:
        raise ValueError(f"{name}: kräver minst {period} datapunkter, fick {len(series)}.")


def sma(close: pd.Series, period: int = 20) -> pd.Series:
    """Enkelt glidande medelvärde (Simple Moving Average).

    Args:
        close: Stängningskurser.
        period: Fönsterlängd.

    Returns:
        SMA-serie; de första ``period - 1`` värdena är NaN.
    """
    _require_min_length(close, period, "SMA")
    return close.rolling(window=period).mean().rename(f"sma_{period}")


def ema(close: pd.Series, period: int = 20) -> pd.Series:
    """Exponentiellt glidande medelvärde (EMA).

    Använder standarddefinitionen med utjämningsfaktor 2/(period+1) och
    SMA för de första ``period`` värdena som startvärde (som de flesta
    handelsplattformar).

    Args:
        close: Stängningskurser.
        period: Fönsterlängd.

    Returns:
        EMA-serie; de första ``period - 1`` värdena är NaN.
    """
    _require_min_length(close, period, "EMA")
    values = close.astype(float)
    result = pd.Series(float("nan"), index=values.index, name=f"ema_{period}")
    alpha = 2.0 / (period + 1)
    current = values.iloc[:period].mean()  # startvärde = SMA över första perioden
    result.iloc[period - 1] = current
    for i in range(period, len(values)):
        current = alpha * values.iloc[i] + (1 - alpha) * current
        result.iloc[i] = current
    return result


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index enligt Wilders originalmetod.

    Första värdet baseras på enkla medelvärden av vinster/förluster över
    ``period`` dagar; därefter Wilders utjämning.

    Args:
        close: Stängningskurser.
        period: Fönsterlängd (standard 14).

    Returns:
        RSI-serie (0–100); de första ``period`` värdena är NaN.
    """
    _require_min_length(close, period + 1, "RSI")
    delta = close.astype(float).diff()
    gains = delta.clip(lower=0.0)
    losses = (-delta).clip(lower=0.0)
    result = pd.Series(float("nan"), index=close.index, name=f"rsi_{period}")
    # Startvärden: enkla medelvärden över de första `period` förändringarna.
    avg_gain = gains.iloc[1 : period + 1].mean()
    avg_loss = losses.iloc[1 : period + 1].mean()
    for i in range(period, len(close)):
        if i > period:  # Wilders utjämning efter startvärdet
            avg_gain = (avg_gain * (period - 1) + gains.iloc[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses.iloc[i]) / period
        if avg_loss == 0:
            result.iloc[i] = 100.0
        else:
            result.iloc[i] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return result


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD: skillnaden mellan snabb och långsam EMA plus signallinje.

    Args:
        close: Stängningskurser.
        fast: Period för snabb EMA.
        slow: Period för långsam EMA.
        signal: Period för signallinjens EMA.

    Returns:
        DataFrame med kolumnerna ``macd``, ``signal`` och ``histogram``.
    """
    if fast >= slow:
        raise ValueError(f"MACD: fast ({fast}) måste vara < slow ({slow}).")
    _require_min_length(close, slow + signal, "MACD")
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.dropna().pipe(ema, signal).reindex(close.index)
    return pd.DataFrame(
        {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": macd_line - signal_line,
        }
    )


def bollinger_bands(close: pd.Series, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """Bollingerband: SMA ± ``num_std`` standardavvikelser.

    Standardavvikelsen är populationsvarianten (ddof=0), som i John
    Bollingers originaldefinition.

    Returns:
        DataFrame med kolumnerna ``middle``, ``upper`` och ``lower``.
    """
    _require_min_length(close, period, "Bollinger")
    middle = sma(close, period)
    std = close.rolling(window=period).std(ddof=0)
    return pd.DataFrame(
        {
            "middle": middle,
            "upper": middle + num_std * std,
            "lower": middle - num_std * std,
        }
    )


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range med Wilders utjämning.

    True range = max(high-low, |high-föregående close|, |low-föregående close|).

    Returns:
        ATR-serie; de första ``period`` värdena är NaN.
    """
    _require_min_length(close, period + 1, "ATR")
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    result = true_range.copy()
    result.iloc[: period + 1] = float("nan")
    # Seed: enkelt medel av TR dag 1..period (dag 0 saknar föregående close).
    current = true_range.iloc[1 : period + 1].mean()
    result.iloc[period] = current
    for i in range(period + 1, len(close)):
        current = (current * (period - 1) + true_range.iloc[i]) / period
        result.iloc[i] = current
    return result.rename(f"atr_{period}")


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume: kumulativ volym med tecken från kursriktningen.

    Returns:
        OBV-serie som startar på 0.
    """
    if len(close) != len(volume):
        raise ValueError("OBV: close och volume måste ha samma längd.")
    if len(close) == 0:
        raise ValueError("OBV: tomma serier.")
    direction = close.diff().apply(
        lambda d: 0.0 if pd.isna(d) or d == 0 else (1.0 if d > 0 else -1.0)
    )
    return (direction * volume.astype(float)).cumsum().rename("obv")


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """Volume Weighted Average Price, återställd per handelsdag.

    Standardreferens i intradagshandel: kumulativt volymvägt snitt av
    typiskt pris (H+L+C)/3 sedan dagens öppning. Kräver intradagsdata
    med klockslag i indexet — på dagsdata blir VWAP = typiskt pris.

    Args:
        high: Högsta pris per bar.
        low: Lägsta pris per bar.
        close: Stängningskurs per bar.
        volume: Volym per bar.

    Returns:
        VWAP-serie alignad med indata. Barer med noll ackumulerad volym
        (t.ex. index) ger NaN — aldrig ett gissat värde.
    """
    if not len(high) == len(low) == len(close) == len(volume):
        raise ValueError("VWAP: alla serier måste ha samma längd.")
    if len(close) == 0:
        raise ValueError("VWAP: tomma serier.")
    typical_price = (high + low + close) / 3.0
    session = close.index.normalize()
    weighted = (typical_price * volume).groupby(session).cumsum()
    cumulative_volume = volume.groupby(session).cumsum()
    return (weighted / cumulative_volume.replace(0.0, float("nan"))).rename("vwap")


def compute_all(prices: pd.DataFrame) -> pd.DataFrame:
    """Beräknar en standarduppsättning indikatorer för en OHLCV-frame.

    Args:
        prices: DataFrame med kolumnerna open/high/low/close/volume.

    Returns:
        Ny DataFrame med priser + indikatorkolumner. Rader där en viss
        indikator inte är definierad ännu innehåller NaN.
    """
    required = {"high", "low", "close", "volume"}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"Prisdata saknar kolumner: {sorted(missing)}")
    result = prices.copy()
    close = prices["close"]
    result["sma_20"] = sma(close, 20)
    result["sma_50"] = sma(close, 50) if len(close) >= 50 else float("nan")
    result["sma_200"] = sma(close, 200) if len(close) >= 200 else float("nan")
    result["ema_20"] = ema(close, 20)
    result["rsi_14"] = rsi(close, 14)
    result = result.join(macd(close))
    result = result.join(bollinger_bands(close, 20).add_prefix("bb_"))
    result["atr_14"] = atr(prices["high"], prices["low"], close, 14)
    result["obv"] = obv(close, prices["volume"])
    return result
