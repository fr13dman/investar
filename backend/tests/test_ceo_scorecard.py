from datetime import date

import pytest

from app.models import CeoOverride, Company, Executive
from app.providers import registry
from app.providers.wikidata import Tenure
from app.providers.xbrl import parse_instance
from app.services import ceo_scorecard as svc
from tests.conftest import fixture_bytes
from tests.fakes import FakeIntraday, FakeSec, FakeWikidata

TENURES = [Tenure("Steve Jobs", date(1997, 9, 1), date(2011, 8, 23)), Tenure("Tim Cook", date(2011, 8, 24), None)]


def test_names_match():
    assert svc.names_match("Mr. Timothy D. Cook", "Tim Cook")  # nicknames match on surname
    assert svc.names_match("Mr. Timothy D. Cook", "Timothy Cook")
    assert svc.names_match("Satya Nadella", "Mr. Satya  Nadella")
    assert not svc.names_match("Jane Smith", "John Smithers")
    assert not svc.names_match(None, "x")


def test_resolve_ceo_prefers_override_then_wikidata():
    name, start, source = svc.resolve_ceo(None, "Mr. Timothy Cook", [*TENURES[:1], Tenure("Timothy Cook", date(2011, 8, 24), None)])
    assert (name, start, source) == ("Timothy Cook", date(2011, 8, 24), "wikidata")

    override = CeoOverride(ticker="AAPL", ceo_name="Someone Else", tenure_start=date(2020, 1, 1))
    assert svc.resolve_ceo(override, "Mr. Timothy Cook", TENURES) == ("Someone Else", date(2020, 1, 1), "manual")

    # No executive name: fall back to Wikidata's current CEO.
    assert svc.resolve_ceo(None, None, TENURES) == ("Tim Cook", date(2011, 8, 24), "wikidata")


def test_resolve_ceo_unlabeled_wikidata_entry():
    tenures = [Tenure("Tim Cook", date(2011, 8, 24), date(2026, 8, 31)), Tenure("Q106028933", date(2026, 9, 1), None)]
    assert svc.resolve_ceo(None, "Mr. John Ternus", tenures) == ("John Ternus", date(2026, 9, 1), "wikidata-unlabeled")


def test_parse_pay_vs_performance_from_proxy_instance():
    rows = svc.parse_pay_vs_performance(parse_instance(fixture_bytes("sec_def14a_instance.xml")))
    assert [r["fiscal_year_end"] for r in rows][:2] == ["2025-09-27", "2024-09-28"]
    latest = rows[0]
    assert latest["peo_total_comp"] == 74_294_811
    assert latest["peo_comp_actually_paid"] == 108_423_733
    assert latest["tsr_value"] == pytest.approx(233.88)
    assert latest["peer_tsr_value"] == pytest.approx(279.51)
    assert latest["net_income"] == 112_010_000_000
    assert latest["peo_names"] == ["Mr. Cook"]
    assert len(rows) == 5


def test_refresh_ceo_end_to_end_with_fixtures(seeded):
    seeded.get(Company, "AAPL").cik = "0000320193"
    seeded.add(Executive(ticker="AAPL", name="Mr. John Ternus", title="CEO & Director", is_ceo=True))
    seeded.commit()
    registry.override(sec=FakeSec(), wikidata=FakeWikidata(), prices=FakeIntraday())

    card = svc.refresh_ceo(seeded, "AAPL")
    assert card.ceo_name == "John Ternus"
    assert card.tenure_start == date(2026, 9, 1) and card.tenure_source == "wikidata-unlabeled"
    assert card.window_start >= date(2026, 9, 1) and not card.window_truncated
    assert card.tsr_pct is not None and card.spy_tsr_pct is not None
    assert card.excess_return_pct == pytest.approx(card.tsr_pct - card.spy_tsr_pct)
    # FY2025 (baseline, ends before tenure) -> FY2026
    assert card.revenue_cagr_pct == pytest.approx(((478_834 / 416_161) ** (1 / ((date(2026, 9, 26) - date(2025, 9, 27)).days / 365.25)) - 1) * 100, rel=1e-3)
    assert card.margin_end_pct and 15 < card.margin_end_pct < 40
    assert card.pay_vs_performance[0]["peo_total_comp"] == 74_294_811
    assert any(t["name"] == "Tim Cook" for t in card.tenures)


def test_override_recompute_without_network(seeded):
    seeded.get(Company, "AAPL").cik = "0000320193"
    seeded.commit()
    registry.override(sec=FakeSec(), wikidata=FakeWikidata(), prices=FakeIntraday())
    svc.refresh_ceo(seeded, "AAPL")

    class Exploding:
        def __getattr__(self, _):
            raise AssertionError("network used")

    registry.override(sec=Exploding(), wikidata=Exploding())
    seeded.add(CeoOverride(ticker="AAPL", ceo_name="Tim Cook", tenure_start=date(2011, 8, 24)))
    seeded.commit()
    card = svc.recompute_from_stored(seeded, "AAPL")
    assert card.tenure_source == "manual"
    assert card.window_truncated  # tenure predates the 2-year seeded price history
    assert card.pay_vs_performance  # carried over from the stored scorecard


def test_split_factor():
    splits = [(date(2020, 8, 31), 4.0), (date(2024, 6, 10), 10.0)]
    assert svc.split_factor(splits, date(2019, 11, 1)) == 40.0
    assert svc.split_factor(splits, date(2021, 11, 1)) == 10.0
    assert svc.split_factor(splits, date(2025, 1, 1)) == 1.0


def test_eps_is_restated_for_later_splits(seeded):
    from app.models import FinancialFact, StockSplit

    for end, filed, eps in ((date(2019, 9, 28), date(2019, 10, 31), 11.89), (date(2023, 9, 30), date(2023, 11, 3), 6.13)):
        seeded.add(FinancialFact(ticker="AAPL", concept="EarningsPerShareDiluted", period_end=end, unit="USD/shares",
                                 value=eps, filed=filed))
    seeded.add(StockSplit(ticker="AAPL", date=date(2020, 8, 31), ratio=4.0))
    seeded.commit()
    rows = {r["fiscal_year_end"]: r["eps"] for r in svc.fundamentals_table(seeded, "AAPL")}
    assert rows["2019-09-28"] == pytest.approx(11.89 / 4)  # filed before the 4-for-1 split
    assert rows["2023-09-30"] == pytest.approx(6.13)


def test_refresh_ceo_requires_cik(seeded):
    with pytest.raises(ValueError):
        svc.refresh_ceo(seeded, "AAPL")
