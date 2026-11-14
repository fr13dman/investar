from datetime import date

import pandas as pd
import pytest

from app.providers import constituents
from app.providers.base import to_dotted, to_yahoo
from app.providers.prices_yfinance import parse_download, parse_profile


def _sp500_html(n: int = 400) -> str:
    rows = "".join(
        f"<tr><td>T{i}</td><td>Company {i}</td><td>Industrials</td><td>Machinery</td><td>City</td>"
        f"<td>2000-01-01</td><td>{1000 + i}</td><td>1900</td></tr>"
        for i in range(n)
    )
    special = ("<tr><td>BRK.B</td><td>Berkshire Hathaway</td><td>Financials</td>"
               "<td>Multi-Sector Holdings</td><td>Omaha</td><td>2010</td><td>1067983</td><td>1839</td></tr>")
    return (
        "<table><tr><th>Symbol</th><th>Security</th><th>GICS Sector</th><th>GICS Sub-Industry</th>"
        "<th>Headquarters Location</th><th>Date added</th><th>CIK</th><th>Founded</th></tr>"
        f"{special}{rows}</table>"
    )


def _ndx_html() -> str:
    rows = "".join(f"<tr><td>N{i}</td><td>Nasdaq Co {i}</td><td>US0000</td><td>Technology</td><td>Software</td></tr>"
                   for i in range(100))
    return ("<table><tr><th>small</th></tr><tr><td>x</td></tr></table>"
            "<table><tr><th>Ticker</th><th>Company</th><th>ISIN</th><th>ICB Industry[2]</th>"
            f"<th>ICB Subsector[2]</th></tr>{rows}</table>")


def test_ticker_normalisation():
    assert to_yahoo("brk.b") == "BRK-B"
    assert to_dotted("BRK-B") == "BRK.B"


def test_parse_sp500():
    rows = constituents.parse_sp500(_sp500_html())
    assert len(rows) == 401
    brk = rows[0]
    assert brk.ticker == "BRK-B"
    assert brk.cik == "0001067983"
    assert brk.gics_sector == "Financials"
    assert brk.gics_sub_industry == "Multi-Sector Holdings"
    assert brk.index == "sp500"


def test_parse_ndx100_picks_the_large_table():
    rows = constituents.parse_ndx100(_ndx_html())
    assert len(rows) == 100
    assert rows[0].ticker == "N0" and rows[0].name == "Nasdaq Co 0" and rows[0].index == "ndx100"


def test_parse_ndx100_missing_table_raises():
    with pytest.raises(ValueError):
        constituents.parse_ndx100("<table><tr><th>Ticker</th></tr><tr><td>A</td></tr></table>")


def test_parse_sec_tickers():
    payload = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple"},
               "1": {"cik_str": 1067983, "ticker": "BRK-B", "title": "Berkshire"}}
    assert constituents.parse_sec_tickers(payload) == {"AAPL": "0000320193", "BRK-B": "0001067983"}


def test_parse_download_multiindex_skips_nan_rows():
    idx = pd.to_datetime(["2026-11-09", "2026-11-10"])
    cols = pd.MultiIndex.from_product([["AAPL", "MSFT"], ["Open", "High", "Low", "Close", "Adj Close", "Volume"]])
    data = [[1, 2, 0.5, 1.5, 1.5, 100, 10, 11, 9, 10.5, 10.4, 200],
            [float("nan")] * 6 + [11, 12, 10, 11.5, 11.4, 300]]
    bars = parse_download(pd.DataFrame(data, index=idx, columns=cols), ["AAPL", "MSFT", "MISSING"])
    assert [(b.ticker, b.date) for b in bars] == [
        ("AAPL", date(2026, 11, 9)), ("MSFT", date(2026, 11, 9)), ("MSFT", date(2026, 11, 10))]
    assert bars[1].adj_close == 10.4 and bars[1].volume == 200


def test_parse_download_flat_frame():
    df = pd.DataFrame({"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Adj Close": [1.4],
                       "Volume": [10]}, index=pd.to_datetime(["2026-01-02"]))
    bars = parse_download(df, ["SPY"])
    assert len(bars) == 1 and bars[0].close == 1.5


def test_parse_profile_officers():
    info = {"sector": "Technology", "industry": "Consumer Electronics", "marketCap": 5e12, "trailingPE": 38.8,
            "sharesOutstanding": 1.45e10, "fullTimeEmployees": 167000, "city": "Cupertino", "state": "CA",
            "country": "United States",
            "companyOfficers": [{"name": "Mr.  John  Doe", "title": "CEO & Director", "totalPay": 1e6, "yearBorn": 1970},
                                {"title": "no name"}]}
    p = parse_profile("AAPL", info)
    assert p.sector == "Technology" and p.employees == 167000
    assert [o.name for o in p.officers] == ["Mr. John Doe"]
    assert p.officers[0].total_pay == 1e6


def test_parse_profile_identity_and_etf_size():
    etf = parse_profile("URA", {"longName": "Global X Uranium ETF", "quoteType": "ETF", "currency": "USD",
                                "exchange": "PCX", "totalAssets": 4.7e9})
    assert (etf.name, etf.quote_type, etf.currency, etf.market_cap) == ("Global X Uranium ETF", "ETF", "USD", 4.7e9)
    stock = parse_profile("NBIS", {"shortName": "Nebius", "quoteType": "EQUITY", "marketCap": 2e10, "totalAssets": 1})
    assert stock.name == "Nebius" and stock.market_cap == 2e10
