"""Provider interfaces. Each data type has one Protocol so a free source (yfinance, Finnhub)
can be swapped for a paid one (FMP, Polygon) without touching services or the API."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol


class ProviderUnavailable(RuntimeError):
    """A data source is not configured or unreachable; an expected condition, not a bug."""


def to_yahoo(ticker: str) -> str:
    return ticker.strip().upper().replace(".", "-")


def to_dotted(ticker: str) -> str:
    return ticker.strip().upper().replace("-", ".")


@dataclass
class ConstituentRow:
    ticker: str
    name: str
    index: str  # "sp500" | "ndx100"
    cik: str | None = None
    gics_sector: str | None = None
    gics_sub_industry: str | None = None
    headquarters: str | None = None
    founded: str | None = None


@dataclass
class PriceBar:
    ticker: str
    date: date
    close: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    adj_close: float | None = None
    volume: float | None = None


@dataclass
class Officer:
    name: str
    title: str | None = None
    total_pay: float | None = None
    year_born: int | None = None


@dataclass
class Profile:
    ticker: str
    sector: str | None = None
    industry: str | None = None
    description: str | None = None
    website: str | None = None
    country: str | None = None
    city: str | None = None
    state: str | None = None
    employees: int | None = None
    shares_outstanding: float | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    exchange: str | None = None
    officers: list[Officer] = field(default_factory=list)


@dataclass
class Quote:
    ticker: str
    price: float
    prev_close: float | None
    day_high: float | None
    day_low: float | None
    as_of: datetime


@dataclass
class NewsItem:
    external_id: str | None
    headline: str
    summary: str | None
    source: str | None
    url: str
    image: str | None
    published_at: datetime


@dataclass
class PatentRecord:
    kind: str  # granted | application
    number: str
    title: str | None
    abstract: str | None
    date: date | None
    cpc_class: str | None
    assignee_name: str | None


class ConstituentsProvider(Protocol):
    def fetch(self) -> list[ConstituentRow]: ...


class PriceProvider(Protocol):
    def history(self, tickers: list[str], period: str = "5y") -> list[PriceBar]: ...

    def recent(self, tickers: list[str]) -> list[PriceBar]: ...

    def splits(self, ticker: str) -> list[tuple[date, float]]: ...

    def intraday(self, ticker: str, period: str, interval: str) -> list[dict]: ...


class ProfileProvider(Protocol):
    def profile(self, ticker: str) -> Profile | None: ...


class QuoteProvider(Protocol):
    def quote(self, ticker: str) -> Quote | None: ...


class NewsProvider(Protocol):
    def company_news(self, ticker: str, start: date, end: date) -> list[NewsItem]: ...
