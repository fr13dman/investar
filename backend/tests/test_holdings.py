from datetime import date

from app.providers.holdings_tickerinside import parse_fund_json
import pytest

from app.providers.holdings_vistashares import parse_as_of, parse_holdings_csv, parse_money, parse_weight
from app.providers.base import HoldingLine, ProviderUnavailable
from app.services.etfs import build_treemap_nodes


SAMPLE_CSV = """fund,as_of,name,ticker,market_value,weight
AIS,"November 13, 2026","Micron Technology Inc",MU,"$55,747,232.06",7.27%
AIS,"November 13, 2026","Advanced Micro Devices Inc",AMD,"$53,230,294.26",6.95%
AIS,"November 13, 2026","Cash and Other",,"$1,000,000.00",1.50%
AIS,"November 13, 2026","Call Option XYZ",,"$500,000.00",0.50%
"""


def test_parse_vistashares_csv_weights_and_kinds():
    fund = parse_holdings_csv("AIS", SAMPLE_CSV)
    assert fund.ticker == "AIS"
    assert fund.as_of == date(2026, 11, 13)
    assert fund.source == "vistashares"
    by_t = {h.ticker: h for h in fund.holdings if h.ticker}
    assert by_t["MU"].weight_pct == 7.27
    assert by_t["AMD"].kind == "equity"
    others = [h for h in fund.holdings if h.kind == "other"]
    assert len(others) == 2


def test_parse_weight_and_as_of():
    assert parse_weight("7.36%") == 7.36
    assert parse_weight("(1.5)") == -1.5
    assert parse_weight("-2.25%") == -2.25
    assert parse_as_of("November 13, 2026") == date(2026, 11, 13)
    assert parse_as_of("2026-11-13") == date(2026, 11, 13)


def test_parse_money_suffixes():
    assert parse_money("$1.12B") == pytest.approx(1.12e9)
    assert parse_money("1.1M") == pytest.approx(1.1e6)
    assert parse_money("500K") == pytest.approx(5e5)


def test_reject_html_and_empty_csv():
    with pytest.raises(ProviderUnavailable):
        parse_holdings_csv("AIS", "<html><body>error</body></html>")
    with pytest.raises(ProviderUnavailable):
        parse_holdings_csv("AIS", "foo,bar\n1,2\n")
    with pytest.raises(ProviderUnavailable):
        parse_holdings_csv("AIS", "fund,as_of,name,ticker,weight\n")


def test_classify_avoids_substring_false_positives():
    fund = parse_holdings_csv(
        "AIS",
        'fund,as_of,name,ticker,weight\nAIS,2026-11-13,"Medically Related Co",MEDX,1.0\n'
        'AIS,2026-11-13,"Input Devices Inc",INPT,1.0\n',
    )
    kinds = {h.ticker: h.kind for h in fund.holdings}
    assert kinds["MEDX"] == "equity"
    assert kinds["INPT"] == "equity"


def test_parse_tickerinside_fractional_weights():
    fund = parse_fund_json("URA", {
        "holdings": {"CCJ": 0.18, "UEC": 0.08, "CASH": 0.74},
        "holdings_as_of": "2026-11-12",
        "aum_b": 4.7,
    })
    assert fund.aum == 4.7e9
    assert fund.as_of == date(2026, 11, 12)
    weights = {h.ticker: h.weight_pct for h in fund.holdings}
    assert weights["CCJ"] == 18.0
    assert abs(sum(weights.values()) - 100) < 0.01


def test_parse_funds_json_aum():
    from app.providers.vistashares_meta import parse_funds_json

    meta = parse_funds_json({
        "funds": [{"ticker": "AIS", "name": "AI Fund", "net_assets": "$1,080,000,000.00"}],
    })
    assert meta["AIS"].aum == 1_080_000_000.0


def test_treemap_top25_plus_other():
    holdings = [
        HoldingLine(ticker=f"T{i}", name=f"Name {i}", weight_pct=2.0, kind="equity") for i in range(30)
    ]
    holdings.append(HoldingLine(ticker=None, name="Cash", weight_pct=10.0, kind="other"))
    nodes = build_treemap_nodes(holdings, {}, "wow")
    equities = [n for n in nodes if n["kind"] == "equity"]
    other = [n for n in nodes if n["kind"] == "other"]
    assert len(equities) == 25
    assert len(other) == 1
    assert other[0]["weight_pct"] == 20.0  # 5 leftover equities * 2 + 10 cash
