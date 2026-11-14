"""Prices and profiles from yfinance (unofficial Yahoo Finance wrapper, ~15 min delayed)."""

import logging
import math
from collections.abc import Iterable

import pandas as pd

from app.config import BACKEND_DIR
from app.providers.base import Officer, PriceBar, Profile

log = logging.getLogger(__name__)
CHUNK = 100


def _yf():
    import yfinance as yf

    cache = BACKEND_DIR / "data" / "yf-cache"
    cache.mkdir(parents=True, exist_ok=True)
    yf.set_tz_cache_location(str(cache))
    return yf


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def parse_download(df: pd.DataFrame, tickers: Iterable[str]) -> list[PriceBar]:
    """Flatten a yf.download(group_by='ticker') frame into PriceBars, skipping empty rows."""
    bars: list[PriceBar] = []
    if df is None or df.empty:
        return bars
    multi = isinstance(df.columns, pd.MultiIndex)
    for t in tickers:
        if multi:
            if t not in df.columns.get_level_values(0):
                continue
            sub = df[t]
        else:
            sub = df
        for idx, row in sub.iterrows():
            close = _num(row.get("Close"))
            if close is None:
                continue
            bars.append(
                PriceBar(
                    ticker=t,
                    date=pd.Timestamp(idx).date(),
                    open=_num(row.get("Open")),
                    high=_num(row.get("High")),
                    low=_num(row.get("Low")),
                    close=close,
                    adj_close=_num(row.get("Adj Close")) or close,
                    volume=_num(row.get("Volume")),
                )
            )
    return bars


def parse_profile(ticker: str, info: dict) -> Profile:
    officers = [
        Officer(
            name=" ".join(str(o.get("name", "")).split()),
            title=o.get("title"),
            total_pay=_num(o.get("totalPay")),
            year_born=o.get("yearBorn"),
        )
        for o in info.get("companyOfficers") or []
        if o.get("name")
    ]
    employees = info.get("fullTimeEmployees")
    return Profile(
        ticker=ticker,
        sector=info.get("sector"),
        industry=info.get("industry"),
        description=info.get("longBusinessSummary"),
        website=info.get("website"),
        country=info.get("country"),
        city=info.get("city"),
        state=info.get("state"),
        employees=int(employees) if employees else None,
        shares_outstanding=_num(info.get("sharesOutstanding")),
        # ETFs have no market cap on Yahoo; assets under management is the closest size measure.
        market_cap=_num(info.get("marketCap")) or _num(info.get("totalAssets")),
        pe_ratio=_num(info.get("trailingPE")),
        exchange=info.get("exchange"),
        officers=officers,
        name=info.get("longName") or info.get("shortName"),
        quote_type=info.get("quoteType"),
        currency=info.get("currency"),
    )


class YFinancePrices:
    def _download(self, tickers: list[str], period: str) -> list[PriceBar]:
        yf = _yf()
        bars: list[PriceBar] = []
        for i in range(0, len(tickers), CHUNK):
            chunk = tickers[i : i + CHUNK]
            df = yf.download(
                chunk,
                period=period,
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=True,
            )
            got = parse_download(df, chunk)
            have = {b.ticker for b in got}
            # yfinance's tz cache can raise "database is locked" under threads; retry serially.
            for t in [t for t in chunk if t not in have]:
                try:
                    retry = yf.download(t, period=period, interval="1d", group_by="ticker",
                                        auto_adjust=False, progress=False, threads=False)
                    got.extend(parse_download(retry, [t]))
                except Exception as exc:  # noqa: BLE001
                    log.warning("price download failed for %s: %s", t, exc)
            bars.extend(got)
        return bars

    def history(self, tickers: list[str], period: str = "5y") -> list[PriceBar]:
        return self._download(tickers, period)

    def recent(self, tickers: list[str]) -> list[PriceBar]:
        # During market hours the last daily bar is the live (delayed) session.
        return self._download(tickers, "5d")

    def splits(self, ticker: str) -> list[tuple]:
        """[(date, ratio)] stock split history, e.g. (2024-06-10, 10.0)."""
        series = _yf().Ticker(ticker).splits
        return [(pd.Timestamp(idx).date(), float(r)) for idx, r in series.items() if r and float(r) > 0]

    def intraday(self, ticker: str, period: str, interval: str) -> list[dict]:
        """Intraday candles for the 1D/1W chart ranges; not stored (daily bars are the source of truth)."""
        df = _yf().Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
        out = []
        for idx, row in df.iterrows():
            close = _num(row.get("Close"))
            if close is None:
                continue
            out.append({"time": int(pd.Timestamp(idx).timestamp()), "open": _num(row.get("Open")),
                        "high": _num(row.get("High")), "low": _num(row.get("Low")), "close": close,
                        "volume": _num(row.get("Volume"))})
        return out


class YFinanceProfiles:
    def profile(self, ticker: str) -> Profile | None:
        try:
            info = _yf().Ticker(ticker).info
        except Exception as exc:  # noqa: BLE001
            log.warning("profile fetch failed for %s: %s", ticker, exc)
            return None
        return parse_profile(ticker, info or {})
