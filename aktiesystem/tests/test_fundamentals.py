"""Tester för screening, nyckeltalstabell och DCF-modellen."""

from __future__ import annotations

import pytest

from src.data_ingestion.base import FundamentalData
from src.fundamentals.dcf import DCFAssumptions, dcf_valuation, sensitivity_table
from src.fundamentals.metrics import MISSING_LABEL, metrics_table, net_debt
from src.fundamentals.screening import Criterion, screen


def _company(ticker: str, **kwargs) -> FundamentalData:
    return FundamentalData(
        ticker=ticker, fetched_at="2026-01-01T00:00:00+00:00", source="test", **kwargs
    )


class TestScreening:
    def test_matches_and_rejects(self) -> None:
        companies = [
            _company("BILLIG", pe_ratio=8.0, debt_to_equity=30.0),
            _company("DYR", pe_ratio=40.0, debt_to_equity=30.0),
        ]
        criteria = [Criterion("pe_ratio", "<", 15), Criterion("debt_to_equity", "<", 100)]
        result = screen(companies, criteria)
        assert result.matches == ["BILLIG"]
        assert result.rejected == ["DYR"]

    def test_missing_data_is_reported_not_assumed(self) -> None:
        companies = [_company("OKANT", pe_ratio=None)]
        result = screen(companies, [Criterion("pe_ratio", "<", 15)])
        assert result.matches == []
        assert result.rejected == []
        assert result.missing_data == {"OKANT": ["pe_ratio"]}

    def test_invalid_field_raises(self) -> None:
        with pytest.raises(ValueError):
            Criterion("hemligt_falt", "<", 1)

    def test_invalid_operator_raises(self) -> None:
        with pytest.raises(ValueError):
            Criterion("pe_ratio", "!=", 1)


class TestMetricsTable:
    def test_missing_values_labelled(self) -> None:
        table = metrics_table(_company("X", pe_ratio=12.3))
        pe_row = table[table["Nyckeltal"] == "P/E (rullande)"]["Värde"].iloc[0]
        pb_row = table[table["Nyckeltal"] == "P/B"]["Värde"].iloc[0]
        assert pe_row == "12.3"
        assert pb_row == MISSING_LABEL

    def test_net_debt(self) -> None:
        assert net_debt(_company("X", total_debt=100.0, total_cash=40.0)) == 60.0
        assert net_debt(_company("X", total_debt=100.0)) is None


class TestDCF:
    def test_hand_computed_single_year(self) -> None:
        # FCF=100, tillväxt 10 %, ränta 10 %, terminal 0 %, 1 prognosår.
        # År 1: 110, diskonterat 110/1.1 = 100.
        # Terminal: 110*1.0/0.10 = 1100, diskonterat 1100/1.1 = 1000.
        # EV = 1100. Nettoskuld 100 -> equity 1000. 10 aktier -> 100/aktie.
        result = dcf_valuation(
            100.0,
            DCFAssumptions(
                growth_rate=0.10, discount_rate=0.10, terminal_growth=0.0, projection_years=1
            ),
            net_debt=100.0,
            shares_outstanding=10.0,
        )
        assert result.enterprise_value == pytest.approx(1100.0)
        assert result.equity_value == pytest.approx(1000.0)
        assert result.value_per_share == pytest.approx(100.0)

    def test_negative_fcf_rejected(self) -> None:
        with pytest.raises(ValueError, match="positivt"):
            dcf_valuation(-50.0, DCFAssumptions())

    def test_terminal_growth_must_be_below_discount(self) -> None:
        with pytest.raises(ValueError):
            DCFAssumptions(discount_rate=0.02, terminal_growth=0.03)

    def test_higher_discount_gives_lower_value(self) -> None:
        low = dcf_valuation(100.0, DCFAssumptions(discount_rate=0.08))
        high = dcf_valuation(100.0, DCFAssumptions(discount_rate=0.12))
        assert high.enterprise_value < low.enterprise_value

    def test_missing_share_count_gives_no_per_share_value(self) -> None:
        result = dcf_valuation(100.0, DCFAssumptions(), shares_outstanding=None)
        assert result.value_per_share is None

    def test_sensitivity_table_shape_and_monotonicity(self) -> None:
        table = sensitivity_table(100.0, DCFAssumptions(), shares_outstanding=10.0)
        assert table.shape == (3, 3)
        # Högre ränta (nedåt i tabellen) ska ge lägre värde i varje kolumn.
        for column in table.columns:
            assert table[column].is_monotonic_decreasing
