"""Offline provider fakes backed by recorded fixtures (real SEC/Wikidata responses for Apple)."""

import json
from datetime import date, datetime

from app.providers.base import NewsItem, Quote
from app.providers.sec_edgar import Filing, parse_filing_index
from app.providers.wikidata import parse_tenures
from tests.conftest import fixture_bytes, fixture_text

TEN_K = Filing("0000320193-26-000026", "10-K", date(2026, 11, 3), "aapl-20260926.htm")
PROXY = Filing("0001308179-26-000008", "DEF 14A", date(2026, 1, 8), "aapl014016-def14a.htm")
DOCS = {
    "aapl-20260926_htm.xml": "sec_10k_instance.xml",
    "aapl014016-def14a_htm.xml": "sec_def14a_instance.xml",
    "a10-kexhibit21109262026.htm": "sec_exhibit21.htm",
}


class FakeSec:
    def __init__(self):
        self.calls: list[str] = []

    def company_facts(self, cik):
        self.calls.append("companyfacts")
        return json.loads(fixture_text("sec_companyfacts_aapl.json"))

    def latest_filing(self, cik, forms):
        self.calls.append(f"latest:{forms[0]}")
        return PROXY if "DEF 14A" in forms else TEN_K

    def filing_index(self, cik, filing):
        return parse_filing_index(fixture_text("sec_def14a_index.htm" if filing is PROXY else "sec_10k_index.htm"))

    def document(self, cik, filing, name):
        self.calls.append(f"doc:{name}")
        return fixture_bytes(DOCS[name])


class FakeWikidata:
    def ceo_tenures(self, cik):
        return parse_tenures(json.loads(fixture_text("wikidata_ceo_aapl.json")))


class FakeNews:
    def company_news(self, ticker, start, end):
        return [
            NewsItem("1", f"{ticker} posts record profits and strong growth", None, "Reuters", f"https://news/{ticker}/1",
                     None, datetime(2026, 11, 9, 14, 0)),
            NewsItem("2", f"{ticker} hit with lawsuit over fraud allegations", "Losses widen", "Bloomberg",
                     f"https://news/{ticker}/2", None, datetime(2026, 11, 8, 9, 30)),
            NewsItem("3", f"{ticker} annual meeting scheduled for March", None, "PR", f"https://news/{ticker}/3", None,
                     datetime(2026, 11, 7, 9, 30)),
        ]


class FakeQuotes:
    def __init__(self, price=250.0, prev=245.0):
        self.price, self.prev = price, prev

    def quote(self, ticker):
        return Quote(ticker, self.price, self.prev, self.price + 1, self.prev - 1, datetime(2026, 11, 10, 15, 0))


class NoQuotes:
    def quote(self, ticker):
        raise RuntimeError("FINNHUB_API_KEY is not set")


class FakeIntraday:
    def splits(self, ticker):
        return [(date(2020, 8, 31), 4.0)] if ticker == "AAPL" else []

    def intraday(self, ticker, period, interval):
        base = 1_762_786_200
        return [{"time": base + i * 300, "open": 100 + i, "high": 101 + i, "low": 99 + i, "close": 100.5 + i,
                 "volume": 1000} for i in range(5)]
