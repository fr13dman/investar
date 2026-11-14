"""S&P 500 and Nasdaq-100 membership from Wikipedia, CIKs from SEC's company_tickers.json."""

import io
import re

import pandas as pd

from app import http
from app.config import get_settings
from app.providers.base import ConstituentRow, to_yahoo

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NDX100_URL = "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def _clean_col(name: object) -> str:
    return re.sub(r"\[\d+\]", "", str(name)).strip()


def _find_table(html: str, ticker_cols: tuple[str, ...], min_rows: int = 90) -> pd.DataFrame:
    for df in pd.read_html(io.StringIO(html)):
        df.columns = [_clean_col(c) for c in df.columns]
        if len(df) >= min_rows and any(c in df.columns for c in ticker_cols):
            return df
    raise ValueError("constituents table not found")


def _opt(row: pd.Series, *cols: str) -> str | None:
    for c in cols:
        if c in row and pd.notna(row[c]):
            return str(row[c]).strip()
    return None


def parse_sp500(html: str) -> list[ConstituentRow]:
    df = _find_table(html, ("Symbol",), min_rows=400)
    rows = []
    for _, r in df.iterrows():
        cik = _opt(r, "CIK")
        rows.append(
            ConstituentRow(
                ticker=to_yahoo(str(r["Symbol"])),
                name=str(r["Security"]).strip(),
                index="sp500",
                cik=str(int(float(cik))).zfill(10) if cik else None,
                gics_sector=_opt(r, "GICS Sector"),
                gics_sub_industry=_opt(r, "GICS Sub-Industry"),
                headquarters=_opt(r, "Headquarters Location"),
                founded=_opt(r, "Founded"),
            )
        )
    return rows


def parse_ndx100(html: str) -> list[ConstituentRow]:
    df = _find_table(html, ("Ticker", "Symbol"))
    tcol = "Ticker" if "Ticker" in df.columns else "Symbol"
    ncol = "Company" if "Company" in df.columns else "Security"
    return [
        ConstituentRow(
            ticker=to_yahoo(str(r[tcol])),
            name=str(r[ncol]).strip(),
            index="ndx100",
            gics_sector=_opt(r, "GICS Sector"),
            gics_sub_industry=_opt(r, "GICS Sub-Industry"),
        )
        for _, r in df.iterrows()
    ]


def parse_sec_tickers(payload: dict) -> dict[str, str]:
    return {to_yahoo(v["ticker"]): str(v["cik_str"]).zfill(10) for v in payload.values()}


class WikipediaConstituents:
    def ciks(self) -> dict[str, str]:
        """Ticker -> zero-padded CIK for every SEC registrant (used for non-index symbols too)."""
        with http.client(get_settings().sec_user_agent) as c:
            http.LIMITERS["sec"].acquire()
            return parse_sec_tickers(c.get(SEC_TICKERS_URL).raise_for_status().json())

    def fetch(self) -> list[ConstituentRow]:
        with http.client() as c:
            sp = parse_sp500(c.get(SP500_URL).raise_for_status().text)
            ndx = parse_ndx100(c.get(NDX100_URL).raise_for_status().text)
        ciks = self.ciks()
        for row in sp + ndx:
            row.cik = row.cik or ciks.get(row.ticker)
        return sp + ndx
