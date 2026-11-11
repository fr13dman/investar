from datetime import date, timedelta

from sqlalchemy import func, select

from app.models import Company, Executive, FetchLog, MetricsSnapshot, PriceDaily, QuoteLatest
from app.providers import registry
from app.providers.base import ConstituentRow, Officer, PriceBar, Profile
from app.services import ingest


class FakeConstituents:
    def fetch(self):
        return [
            ConstituentRow("AAPL", "Apple Inc.", "sp500", cik="0000320193", gics_sector="Information Technology",
                           gics_sub_industry="Technology Hardware"),
            ConstituentRow("JPM", "JPMorgan Chase", "sp500", gics_sector="Financials"),
            ConstituentRow("AAPL", "Apple", "ndx100"),
            ConstituentRow("ASML", "ASML Holding", "ndx100", gics_sector="Information Technology"),
        ]


def _bars(ticker: str, closes: list[float], end: date) -> list[PriceBar]:
    days, d = [], end
    while len(days) < len(closes):
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    return [PriceBar(ticker, day, close=c, open=c, high=c, low=c, adj_close=c, volume=1000)
            for day, c in zip(reversed(days), closes)]


class FakePrices:
    def __init__(self, end: date):
        self.end = end

    def history(self, tickers, period="5y"):
        return [b for t in tickers for b in _bars(t, [100 + i for i in range(30)], self.end)]

    def recent(self, tickers):
        return [b for t in tickers for b in _bars(t, [128, 129, 140], self.end)]


class FakeProfiles:
    def profile(self, ticker):
        if ticker == "JPM":
            return None
        return Profile(ticker=ticker, sector="Technology", industry="Consumer Electronics", city="Cupertino",
                       state="CA", country="United States", shares_outstanding=1e9, pe_ratio=30.0,
                       officers=[Officer("Jane Roe", "Chief Executive Officer"), Officer("Bob", "CFO")])


def test_load_universe_merges_indexes_and_adds_benchmarks(session):
    registry.override(constituents=FakeConstituents())
    assert ingest.load_universe(session) == 3
    aapl = session.get(Company, "AAPL")
    assert aapl.in_sp500 and aapl.in_ndx100
    assert aapl.name == "Apple Inc."
    assert aapl.cik == "0000320193"
    assert aapl.sector == "Technology"  # GICS mapped to the Yahoo taxonomy until a profile exists
    assert aapl.gics_sector == "Information Technology"
    assert session.get(Company, "ASML").in_ndx100 and not session.get(Company, "ASML").in_sp500
    assert session.get(Company, "SPY").is_benchmark and session.get(Company, "QQQ").is_benchmark
    assert session.get(FetchLog, ("universe", "")).status == "ok"


def test_load_universe_clears_removed_members(session):
    session.add(Company(ticker="OLD", name="Removed Co", in_sp500=True))
    session.commit()
    registry.override(constituents=FakeConstituents())
    ingest.load_universe(session)
    old = session.get(Company, "OLD")
    assert not old.in_sp500 and not old.in_ndx100
    assert "OLD" not in ingest.universe_tickers(session)


def test_backfill_then_intraday_refresh(session):
    end = date(2026, 11, 10)
    registry.override(constituents=FakeConstituents(), prices=FakePrices(end))
    ingest.load_universe(session)
    n = ingest.backfill_prices(session)
    assert n == 30 * 5  # 3 companies + SPY + QQQ
    assert session.scalar(select(func.count()).select_from(MetricsSnapshot)) == 5

    ingest.refresh_intraday(session)
    q = session.get(QuoteLatest, "AAPL")
    assert q.price == 140 and q.prev_close == 129
    m = session.get(MetricsSnapshot, "AAPL")
    assert m.price == 140
    assert round(m.chg_1d_pct, 4) == round((140 / 129 - 1) * 100, 4)
    # the last bar was overwritten in place, no duplicates
    assert session.scalar(select(func.count()).select_from(PriceDaily).where(PriceDaily.ticker == "AAPL")) == 30


def test_pick_ceo_prefers_company_level_title():
    titles = ["Chairman", "CEO & President of Specialty Insurance", "CEO, President & Director", None]
    assert ingest.pick_ceo(titles) == 2
    assert ingest.pick_ceo(["CEO of Unit A"]) == 0
    assert ingest.pick_ceo(["CFO", None]) is None


def test_enrich_profiles_sets_sector_and_ceo(session):
    registry.override(constituents=FakeConstituents(), profiles=FakeProfiles())
    ingest.load_universe(session)
    done = ingest.enrich_profiles(session, pause=0)
    assert done == 2
    aapl = session.get(Company, "AAPL")
    assert aapl.sector == "Technology" and aapl.industry == "Consumer Electronics"
    assert aapl.headquarters == "Cupertino, CA, United States"
    # JPM had no profile: its GICS "Financials" is shown under the Yahoo name.
    assert session.get(Company, "JPM").sector == "Financial Services"
    ceos = session.scalars(select(Executive).where(Executive.ticker == "AAPL", Executive.is_ceo)).all()
    assert [c.name for c in ceos] == ["Jane Roe"]
    assert session.get(FetchLog, ("profile", "JPM")).status == "error"
