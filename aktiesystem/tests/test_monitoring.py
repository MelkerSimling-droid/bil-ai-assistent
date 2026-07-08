"""Tester för marknadsbevakningen: regler, dubblettskydd och notifierare."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.monitoring.monitor import AlertState
from src.monitoring.notify import LogNotifier, _escape
from src.monitoring.rules import Alert, evaluate_price_rules, sentiment_alert


def _frame(closes: list[float]) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=len(closes), freq="B", name="date")
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1000.0] * len(closes),
        },
        index=index,
    )


RULES = {
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "sma_cross": True,
    "day_move_percent": 4.0,
    "sentiment_threshold": 0.4,
}


class TestRsiRules:
    def test_crossing_below_oversold_triggers_once(self) -> None:
        # Stigande serie följd av kraftiga fall: RSI korsar ned under 30
        # på sista baren.
        closes = [100.0 + i for i in range(20)] + [115.0, 110.0, 104.0, 97.0, 90.0]
        alerts = evaluate_price_rules("TEST", _frame(closes), RULES)
        assert any(a.rule == "rsi_oversold" for a in alerts)

    def test_staying_oversold_does_not_retrigger(self) -> None:
        # Fortsätter falla dagen efter korsningen: RSI är redan under 30
        # -> ingen ny korsning, inget nytt larm.
        closes = [100.0 + i for i in range(20)] + [115.0, 110.0, 104.0, 97.0, 90.0, 84.0]
        alerts = evaluate_price_rules("TEST", _frame(closes), RULES)
        assert not any(a.rule == "rsi_oversold" for a in alerts)

    def test_calm_market_triggers_nothing(self) -> None:
        closes = [100.0 + 0.1 * i for i in range(40)]
        alerts = evaluate_price_rules("TEST", _frame(closes), RULES)
        assert alerts == []

    def test_message_contains_disclaimer(self) -> None:
        closes = [100.0 + i for i in range(20)] + [115.0, 110.0, 104.0, 97.0, 90.0]
        alerts = evaluate_price_rules("TEST", _frame(closes), RULES)
        assert all("inget råd" in a.message for a in alerts)


class TestSmaCross:
    def test_cross_below_sma200_triggers(self) -> None:
        # 210 dagar svagt stigande, sedan ett fall genom SMA 200.
        closes = [100.0 + 0.05 * i for i in range(210)] + [95.0]
        alerts = evaluate_price_rules("TEST", _frame(closes), RULES)
        assert any(a.rule == "sma_cross" and "nedåt" in a.message for a in alerts)

    def test_too_short_history_is_skipped(self) -> None:
        closes = [100.0] * 50
        alerts = evaluate_price_rules("TEST", _frame(closes), RULES)
        assert not any(a.rule == "sma_cross" for a in alerts)


class TestDayMove:
    def test_large_drop_triggers(self) -> None:
        alerts = evaluate_price_rules("TEST", _frame([100.0] * 30 + [94.0]), RULES)
        assert any(a.rule == "day_move" and "-6.0%" in a.message for a in alerts)

    def test_small_move_does_not_trigger(self) -> None:
        alerts = evaluate_price_rules("TEST", _frame([100.0] * 30 + [101.0]), RULES)
        assert not any(a.rule == "day_move" for a in alerts)


class TestSentimentAlert:
    def test_strongly_negative_triggers(self) -> None:
        alerts = sentiment_alert("TEST", -0.55, 5, RULES, "2026-07-08")
        assert len(alerts) == 1 and "negativt" in alerts[0].title

    def test_needs_at_least_three_headlines(self) -> None:
        assert sentiment_alert("TEST", -0.9, 2, RULES, "2026-07-08") == []

    def test_neutral_sentiment_silent(self) -> None:
        assert sentiment_alert("TEST", 0.1, 10, RULES, "2026-07-08") == []


class TestAlertState:
    def _alert(self, alert_id: str = "T|rsi_oversold|2026-07-08") -> Alert:
        return Alert(alert_id, "T", "rsi_oversold", "titel", "meddelande")

    def test_new_alert_then_duplicate(self, tmp_path: Path) -> None:
        state = AlertState(tmp_path / "alerts.sqlite")
        alert = self._alert()
        assert state.is_new(alert.alert_id)
        state.record(alert)
        assert not state.is_new(alert.alert_id)

    def test_recent_returns_history(self, tmp_path: Path) -> None:
        state = AlertState(tmp_path / "alerts.sqlite")
        state.record(self._alert("a|r|1"))
        state.record(self._alert("b|r|2"))
        assert len(state.recent()) == 2


class TestNotifiers:
    def test_log_notifier_always_succeeds(self) -> None:
        assert LogNotifier().send("titel", "meddelande") is True

    def test_applescript_escaping(self) -> None:
        assert _escape('sa "hej"\nrad2') == 'sa \\"hej\\" rad2'
