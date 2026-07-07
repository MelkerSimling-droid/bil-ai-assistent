"""Tester för sentimentmodulen (körs offline — VADER är ett lokalt lexikon)."""

from __future__ import annotations

from src.data_ingestion.base import NewsItem
from src.sentiment.news_sentiment import aggregate_sentiment, score_headlines


def _news(
    title: str, ticker: str = "TEST", published: str | None = "2026-07-01T08:00:00+00:00"
) -> NewsItem:
    return NewsItem(ticker=ticker, title=title, publisher="Test", published_at=published, url=None)


class TestScoring:
    def test_positive_headline(self) -> None:
        scored = score_headlines([_news("Company reports excellent record profits, stock soars")])
        assert scored[0].label == "positiv"
        assert scored[0].compound > 0

    def test_negative_headline(self) -> None:
        scored = score_headlines([_news("Company crashes after terrible fraud scandal")])
        assert scored[0].label == "negativ"
        assert scored[0].compound < 0

    def test_neutral_headline(self) -> None:
        scored = score_headlines([_news("Company announces quarterly report date")])
        assert scored[0].label == "neutral"

    def test_empty_titles_skipped(self) -> None:
        assert score_headlines([_news("   ")]) == []


class TestAggregation:
    def test_grouped_by_ticker_and_day(self) -> None:
        scored = score_headlines(
            [
                _news("Great excellent news", published="2026-07-01T08:00:00"),
                _news("Awful terrible news", published="2026-07-01T12:00:00"),
                _news("Great excellent news", published="2026-07-02T08:00:00"),
            ]
        )
        result = aggregate_sentiment(scored)
        assert len(result) == 2
        first_day = result[result["datum"] == "2026-07-01"].iloc[0]
        assert first_day["antal_rubriker"] == 2

    def test_missing_date_labelled_not_invented(self) -> None:
        scored = score_headlines([_news("Some news", published=None)])
        result = aggregate_sentiment(scored)
        assert result.iloc[0]["datum"] == "okänt datum"

    def test_empty_input_gives_empty_frame(self) -> None:
        result = aggregate_sentiment([])
        assert result.empty
