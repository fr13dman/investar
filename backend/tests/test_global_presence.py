from datetime import date

import pytest

from app.models import Company
from app.providers import registry
from app.providers.xbrl import parse_instance
from app.services.countries import country_from_xbrl_member, resolve_country
from app.services.global_presence import extract_geo_revenue, global_payload, humanize_member, parse_exhibit21, refresh_global
from tests.conftest import fixture_bytes, fixture_text
from tests.fakes import FakeSec


@pytest.mark.parametrize(
    "text,alpha2",
    [
        ("Delaware", "US"), ("Delaware, U.S.", "US"), ("New York, USA", "US"), ("Georgia", "US"),
        ("England and Wales", "GB"), ("United Kingdom", "GB"), ("Scotland", "GB"), ("The Netherlands", "NL"),
        ("Korea", "KR"), ("Republic of Korea", "KR"), ("PRC", "CN"), ("People's Republic of China", "CN"),
        ("Hong Kong SAR", "HK"), ("Cayman Islands", "KY"), ("British Virgin Islands", "VG"),
        ("U.S. Virgin Islands", "VI"), ("Ontario, Canada", "CA"), ("Turkey", "TR"), ("Puerto Rico", "PR"),
        ("Singapore", "SG"), ("Province of Quebec, Canada", "CA"), ("Grand Duchy of Luxembourg", "LU"),
    ],
)
def test_resolve_country(text, alpha2):
    assert resolve_country(text).alpha2 == alpha2


def test_resolve_country_unknown():
    assert resolve_country("") is None
    assert resolve_country("Atlantis") is None
    assert resolve_country(None) is None


def test_country_from_member():
    assert country_from_xbrl_member("country:US").name == "United States"
    assert country_from_xbrl_member("aapl:OtherCountriesMember") is None


def test_parse_exhibit21_table_format():
    pairs = parse_exhibit21(fixture_text("sec_exhibit21.htm"))
    assert len(pairs) == 20
    assert pairs[0] == ("Apple Asia Limited", "Hong Kong")
    assert ("Braeburn Capital, Inc.", "Nevada, U.S.") in pairs
    assert all("Jurisdiction" not in j for _, j in pairs)


def test_parse_exhibit21_text_formats():
    html = """<html><body><p>EXHIBIT 21</p><p>Subsidiaries of Example Corp</p>
      <p>Example Holdings LLC (Delaware)</p><p>Example GmbH (Germany)</p><p>Example KK – Japan</p>
      <p>Ireland:</p><p>Example Ireland Ltd</p><p>Example Finance DAC</p></body></html>"""
    pairs = parse_exhibit21(html)
    assert pairs == [
        ("Example Holdings LLC", "Delaware"), ("Example GmbH", "Germany"), ("Example KK", "Japan"),
        ("Example Ireland Ltd", "Ireland"), ("Example Finance DAC", "Ireland"),
    ]


def test_humanize_member():
    assert humanize_member("country:CN") == "China"
    assert humanize_member("aapl:RestOfAsiaPacificSegmentMember") == "Rest Of Asia Pacific"
    assert humanize_member("us-gaap:NonUsMember") == "Non-US"
    assert humanize_member("srt:AmericasMember") == "Americas"


def test_extract_geo_revenue_from_10k_instance():
    rows = extract_geo_revenue(parse_instance(fixture_bytes("sec_10k_instance.xml")))
    latest_geo = {r["region"]: r["revenue"] for r in rows if r["axis"] == "geographic" and r["period_end"] == date(2026, 9, 26)}
    assert latest_geo == {"United States": 167_746e6, "China": 82_378e6, "Other Countries": 228_710e6}
    segments = {r["region"] for r in rows if r["axis"] == "segment"}
    assert segments == {"Americas", "Europe", "Greater China", "Japan", "Rest Of Asia Pacific"}
    assert {r["period_end"] for r in rows} == {date(2024, 9, 28), date(2025, 9, 27), date(2026, 9, 26)}
    us = next(r for r in rows if r["region"] == "United States")
    assert us["country_alpha2"] == "US"


def test_header_rows_and_subtotals_are_skipped():
    html = """<table><tr><td>December 31, 2025 Name</td><td>Organized Under The Laws Of</td></tr>
      <tr><td>Name</td><td>Where Incorporated</td></tr><tr><td>JPMorgan Chase Bank, N.A.</td><td>United States</td></tr>
      <tr><td>Acme Health Organization Inc.</td><td>Delaware</td></tr></table>"""
    assert parse_exhibit21(html) == [("JPMorgan Chase Bank, N.A.", "United States"), ("Acme Health Organization Inc.", "Delaware")]

    from app.providers.xbrl import Context, Fact

    def fact(member, value):
        ctx = Context(member, date(2025, 1, 1), date(2025, 12, 31), {"srt:StatementGeographicalAxis": member})
        return Fact("us-gaap", "Revenues", value, ctx, "usd")

    rows = extract_geo_revenue([fact("srt:NorthAmericaMember", "60"), fact("jpm:EMEAMember", "25"),
                                fact("jpm:TotalInternationalMember", "40"), fact("srt:LatinAmericaMember", "15")])
    assert {r["region"] for r in rows} == {"North America", "EMEA", "Latin America"}


def test_product_segments_are_not_reported_as_geography():
    from app.providers.xbrl import Context, Fact

    ctx = Context("c1", date(2025, 1, 1), date(2025, 12, 31), {"us-gaap:StatementBusinessSegmentsAxis": "x:CloudMember"})
    facts = [Fact("us-gaap", "Revenues", "100", ctx, "usd")]
    assert extract_geo_revenue(facts) == []


def test_refresh_global_and_payload(seeded):
    seeded.get(Company, "AAPL").cik = "0000320193"
    seeded.commit()
    registry.override(sec=FakeSec())
    refresh_global(seeded, "AAPL")
    body = global_payload(seeded, "AAPL", "0000320193")
    assert len(body["subsidiaries"]) == 20 and body["unmapped"] == 0
    countries = {c["alpha2"]: c["count"] for c in body["countries"]}
    assert countries["IE"] == 3 and countries["US"] == 3 and countries["JP"] == 2
    ireland = next(c for c in body["countries"] if c["alpha2"] == "IE")
    assert ireland["numeric"] == "372"
    first = body["revenue_by_region"][0]
    assert first["axis"] == "geographic" and first["period_end"] == "2026-09-26"
    assert sum(r["share_pct"] for r in first["regions"]) == pytest.approx(100)
    assert first["regions"][0]["region"] == "Other Countries"
    assert body["filing"]["url"].endswith("/000032019326000026/0000320193-26-000026-index.htm")


def test_global_endpoint(client, seeded):
    seeded.get(Company, "AAPL").cik = "0000320193"
    seeded.commit()
    registry.override(sec=FakeSec())
    assert client.get("/api/companies/AAPL/global").json()["refresh"]["refreshing"] is True
    body = client.get("/api/companies/AAPL/global").json()
    # HK, US, CA, CN, IE, GB, IN, JP, KR, MX, AU, SG, TH, VN
    assert body["refresh"]["status"] == "ok" and len(body["countries"]) == 14
