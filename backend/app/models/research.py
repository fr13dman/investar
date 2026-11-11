import datetime as dt

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

_FK = dict(ondelete="CASCADE")


class Executive(Base):
    __tablename__ = "executives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(12), ForeignKey("companies.ticker", **_FK), index=True)
    name: Mapped[str] = mapped_column(String(200))
    title: Mapped[str | None] = mapped_column(String(200))
    total_pay: Mapped[float | None] = mapped_column(Float)
    year_born: Mapped[int | None] = mapped_column(Integer)
    is_ceo: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str] = mapped_column(String(20), default="yfinance")


class CeoOverride(Base):
    __tablename__ = "ceo_overrides"

    ticker: Mapped[str] = mapped_column(String(12), ForeignKey("companies.ticker", **_FK), primary_key=True)
    ceo_name: Mapped[str | None] = mapped_column(String(200))
    tenure_start: Mapped[dt.date | None] = mapped_column(Date)


class CeoScorecard(Base):
    __tablename__ = "ceo_scorecard"

    ticker: Mapped[str] = mapped_column(String(12), ForeignKey("companies.ticker", **_FK), primary_key=True)
    ceo_name: Mapped[str | None] = mapped_column(String(200))
    tenure_start: Mapped[dt.date | None] = mapped_column(Date)
    tenure_source: Mapped[str | None] = mapped_column(String(20))
    tenures: Mapped[list | None] = mapped_column(JSON)
    window_start: Mapped[dt.date | None] = mapped_column(Date)
    window_truncated: Mapped[bool] = mapped_column(default=False)
    tsr_pct: Mapped[float | None] = mapped_column(Float)
    spy_tsr_pct: Mapped[float | None] = mapped_column(Float)
    excess_return_pct: Mapped[float | None] = mapped_column(Float)
    tsr_annualized_pct: Mapped[float | None] = mapped_column(Float)
    spy_annualized_pct: Mapped[float | None] = mapped_column(Float)
    revenue_cagr_pct: Mapped[float | None] = mapped_column(Float)
    eps_cagr_pct: Mapped[float | None] = mapped_column(Float)
    margin_start_pct: Mapped[float | None] = mapped_column(Float)
    margin_end_pct: Mapped[float | None] = mapped_column(Float)
    fundamentals: Mapped[list | None] = mapped_column(JSON)
    pay_vs_performance: Mapped[list | None] = mapped_column(JSON)
    computed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)


class FinancialFact(Base):
    """Annual (FY, ~12 month duration) facts from SEC companyfacts, keyed by period end."""

    __tablename__ = "financial_facts"

    ticker: Mapped[str] = mapped_column(String(12), ForeignKey("companies.ticker", **_FK), primary_key=True)
    concept: Mapped[str] = mapped_column(String(80), primary_key=True)
    period_end: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    unit: Mapped[str] = mapped_column(String(20), primary_key=True)
    period_start: Mapped[dt.date | None] = mapped_column(Date)
    value: Mapped[float] = mapped_column(Float)
    form: Mapped[str | None] = mapped_column(String(10))
    filed: Mapped[dt.date | None] = mapped_column(Date)


class StockSplit(Base):
    __tablename__ = "stock_splits"

    ticker: Mapped[str] = mapped_column(String(12), ForeignKey("companies.ticker", **_FK), primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    ratio: Mapped[float] = mapped_column(Float)  # e.g. 10.0 for a 10-for-1 split


class NewsArticle(Base):
    __tablename__ = "news"
    __table_args__ = (UniqueConstraint("ticker", "url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(12), ForeignKey("companies.ticker", **_FK), index=True)
    external_id: Mapped[str | None] = mapped_column(String(40))
    headline: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(Text)
    image: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[dt.datetime] = mapped_column(DateTime, index=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(10))
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    sentiment_model: Mapped[str | None] = mapped_column(String(20))


class Subsidiary(Base):
    __tablename__ = "subsidiaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(12), ForeignKey("companies.ticker", **_FK), index=True)
    name: Mapped[str] = mapped_column(String(300))
    jurisdiction: Mapped[str | None] = mapped_column(String(200))
    country_name: Mapped[str | None] = mapped_column(String(100))
    country_alpha2: Mapped[str | None] = mapped_column(String(2))
    country_numeric: Mapped[str | None] = mapped_column(String(3))
    filing_accession: Mapped[str | None] = mapped_column(String(25))


class GeoRevenue(Base):
    __tablename__ = "geo_revenue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(12), ForeignKey("companies.ticker", **_FK), index=True)
    period_end: Mapped[dt.date] = mapped_column(Date)
    region: Mapped[str] = mapped_column(String(150))
    member: Mapped[str] = mapped_column(String(200))
    axis: Mapped[str] = mapped_column(String(20), default="geographic")  # geographic | segment
    country_alpha2: Mapped[str | None] = mapped_column(String(2))
    revenue: Mapped[float] = mapped_column(Float)
    concept: Mapped[str | None] = mapped_column(String(100))
    filing_accession: Mapped[str | None] = mapped_column(String(25))


class PatentAssigneeMap(Base):
    __tablename__ = "patent_assignee_map"
    __table_args__ = (UniqueConstraint("ticker", "assignee_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(12), ForeignKey("companies.ticker", **_FK), index=True)
    assignee_name: Mapped[str] = mapped_column(String(300))
    match: Mapped[str] = mapped_column(String(10), default="exact")  # exact | prefix
    source: Mapped[str] = mapped_column(String(20), default="auto")  # auto | curated | manual


class Patent(Base):
    __tablename__ = "patents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # "{kind}:{number}:{ticker}"
    ticker: Mapped[str] = mapped_column(String(12), ForeignKey("companies.ticker", **_FK), index=True)
    kind: Mapped[str] = mapped_column(String(12))  # granted | application
    number: Mapped[str] = mapped_column(String(30))
    title: Mapped[str | None] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text)
    date: Mapped[dt.date | None] = mapped_column(Date, index=True)
    cpc_class: Mapped[str | None] = mapped_column(String(10))
    assignee_name: Mapped[str | None] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(20), default="patentsview_api")


class PatentStat(Base):
    """Aggregates: yearly counts (dimension='year') and CPC class counts (dimension='cpc')."""

    __tablename__ = "patent_stats"

    ticker: Mapped[str] = mapped_column(String(12), ForeignKey("companies.ticker", **_FK), primary_key=True)
    kind: Mapped[str] = mapped_column(String(12), primary_key=True)
    dimension: Mapped[str] = mapped_column(String(10), primary_key=True)
    key: Mapped[str] = mapped_column(String(20), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
