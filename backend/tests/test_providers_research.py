import json
from datetime import date

import pytest

from app.providers.news_finnhub import parse_news
from app.providers.quotes_finnhub import parse_quote
from app.providers.sec_edgar import (
    REVENUE_CONCEPTS,
    annual_facts,
    find_exhibit21,
    find_instance_document,
    parse_filing_index,
    parse_filings,
)
from app.providers.wikidata import parse_tenures
from app.providers.xbrl import parse_instance
from tests.conftest import fixture_bytes, fixture_text


def test_parse_quote():
    q = parse_quote("AAPL", {"c": 201.5, "pc": 199.0, "h": 202, "l": 198, "t": 1_762_790_400})
    assert q.price == 201.5 and q.prev_close == 199.0 and q.day_high == 202
    assert parse_quote("NOPE", {"c": 0, "pc": 0}) is None


def test_parse_news_dedupes_and_skips_incomplete():
    payload = [
        {"id": 1, "headline": " Apple beats estimates ", "summary": "", "source": "Reuters", "url": "https://x/1", "datetime": 1_762_790_400},
        {"id": 2, "headline": "dup", "url": "https://x/1", "datetime": 1_762_790_400},
        {"id": 3, "headline": "", "url": "https://x/3"},
        {"id": 4, "headline": "No url"},
    ]
    items = parse_news(payload)
    assert len(items) == 1
    assert items[0].headline == "Apple beats estimates" and items[0].summary is None and items[0].external_id == "1"


def test_parse_filings_sorted_and_filtered():
    sub = {"filings": {"recent": {
        "accessionNumber": ["a1", "a2", "a3"], "form": ["10-K", "8-K", "10-K"],
        "filingDate": ["2024-11-01", "2025-01-01", "2025-10-31"], "primaryDocument": ["k24.htm", "x.htm", "k25.htm"],
    }}}
    filings = parse_filings(sub, ("10-K",))
    assert [f.accession for f in filings] == ["a3", "a1"]


def test_filing_index_finds_instance_and_exhibit21():
    entries = parse_filing_index(fixture_text("sec_10k_index.htm"))
    assert entries[0].document == "aapl-20260926.htm" and entries[0].type == "10-K"
    assert find_exhibit21(entries) == "a10-kexhibit21109262026.htm"
    assert find_instance_document(entries) == "aapl-20260926_htm.xml"
    proxy = parse_filing_index(fixture_text("sec_def14a_index.htm"))
    assert find_instance_document(proxy) == "aapl014016-def14a_htm.xml"
    assert find_exhibit21(proxy) is None


def test_annual_facts_from_companyfacts():
    cf = json.loads(fixture_text("sec_companyfacts_aapl.json"))
    revenue = annual_facts(cf, REVENUE_CONCEPTS, "USD")
    ends = [f.end for f in revenue]
    assert ends == sorted(ends) and len(ends) == len(set(ends))
    fy2026 = next(f for f in revenue if f.end == date(2026, 9, 26))
    # Matches the sum of the geographic facts in the 10-K instance (US + China + other countries).
    assert fy2026.value == pytest.approx(167_746e6 + 82_378e6 + 228_710e6)
    assert all(330 <= (f.end - f.start).days <= 400 for f in revenue)
    eps = annual_facts(cf, ["EarningsPerShareDiluted"], "USD/shares")
    assert eps and eps[-1].value > 0


def test_parse_instance_contexts_and_dims():
    facts = parse_instance(fixture_bytes("sec_10k_instance.xml"))
    geo = [f for f in facts if "srt:StatementGeographicalAxis" in f.context.dims]
    assert {f.context.dims["srt:StatementGeographicalAxis"] for f in geo} >= {"country:US", "country:CN"}
    assert all(f.prefix == "us-gaap" for f in geo)
    assert geo[0].context.duration_days and geo[0].context.duration_days > 300


def test_parse_tenures_sorted():
    tenures = parse_tenures(json.loads(fixture_text("wikidata_ceo_aapl.json")))
    assert tenures[0].name == "Michael Scott"
    cook = next(t for t in tenures if t.name == "Tim Cook")
    assert cook.start == date(2011, 8, 24)
    assert tenures[-1].end is None
