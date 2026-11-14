import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Company(Base):
    __tablename__ = "companies"

    ticker: Mapped[str] = mapped_column(String(12), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    cik: Mapped[str | None] = mapped_column(String(10), index=True)
    exchange: Mapped[str | None] = mapped_column(String(20))
    sector: Mapped[str | None] = mapped_column(String(80), index=True)
    industry: Mapped[str | None] = mapped_column(String(120), index=True)
    gics_sector: Mapped[str | None] = mapped_column(String(80))
    gics_sub_industry: Mapped[str | None] = mapped_column(String(120))
    in_sp500: Mapped[bool] = mapped_column(Boolean, default=False)
    in_ndx100: Mapped[bool] = mapped_column(Boolean, default=False)
    is_benchmark: Mapped[bool] = mapped_column(Boolean, default=False)
    asset_type: Mapped[str] = mapped_column(String(10), default="stock", server_default="stock")
    # Why a non-index symbol is tracked: "curated" (niche catalog) or "user" (added from Explore).
    extra_source: Mapped[str | None] = mapped_column(String(10), index=True)
    website: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    headquarters: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(80))
    employees: Mapped[int | None] = mapped_column(Integer)
    founded: Mapped[str | None] = mapped_column(String(40))
    shares_outstanding: Mapped[float | None] = mapped_column(Float)
    market_cap: Mapped[float | None] = mapped_column(Float)
    pe_ratio: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[dt.datetime | None] = mapped_column(DateTime, onupdate=func.now())


class PriceDaily(Base):
    __tablename__ = "prices_daily"

    ticker: Mapped[str] = mapped_column(
        String(12), ForeignKey("companies.ticker", ondelete="CASCADE"), primary_key=True
    )
    date: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    adj_close: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)


class QuoteLatest(Base):
    __tablename__ = "quotes_latest"

    ticker: Mapped[str] = mapped_column(
        String(12), ForeignKey("companies.ticker", ondelete="CASCADE"), primary_key=True
    )
    price: Mapped[float] = mapped_column(Float)
    prev_close: Mapped[float | None] = mapped_column(Float)
    day_high: Mapped[float | None] = mapped_column(Float)
    day_low: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(20), default="yfinance")
    as_of: Mapped[dt.datetime] = mapped_column(DateTime)


class MetricsSnapshot(Base):
    __tablename__ = "metrics_snapshot"

    ticker: Mapped[str] = mapped_column(
        String(12), ForeignKey("companies.ticker", ondelete="CASCADE"), primary_key=True
    )
    price: Mapped[float | None] = mapped_column(Float)
    market_cap: Mapped[float | None] = mapped_column(Float, index=True)
    pe_ratio: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    week52_high: Mapped[float | None] = mapped_column(Float)
    week52_low: Mapped[float | None] = mapped_column(Float)
    chg_1d_pct: Mapped[float | None] = mapped_column(Float, index=True)
    chg_1d_abs: Mapped[float | None] = mapped_column(Float)
    chg_1w_pct: Mapped[float | None] = mapped_column(Float, index=True)
    chg_1w_abs: Mapped[float | None] = mapped_column(Float)
    chg_ytd_pct: Mapped[float | None] = mapped_column(Float, index=True)
    chg_ytd_abs: Mapped[float | None] = mapped_column(Float)
    sparkline: Mapped[list | None] = mapped_column(JSON)
    as_of: Mapped[dt.datetime | None] = mapped_column(DateTime)


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    watchlist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("watchlists.id", ondelete="CASCADE"), primary_key=True
    )
    ticker: Mapped[str] = mapped_column(
        String(12), ForeignKey("companies.ticker", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class Niche(Base):
    """Two-level thematic grouping (e.g. AI > Neoclouds) that cuts across Yahoo sectors."""

    __tablename__ = "niches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("niches.id", ondelete="CASCADE"), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class NicheMember(Base):
    __tablename__ = "niche_members"

    niche_id: Mapped[int] = mapped_column(Integer, ForeignKey("niches.id", ondelete="CASCADE"), primary_key=True)
    ticker: Mapped[str] = mapped_column(
        String(12), ForeignKey("companies.ticker", ondelete="CASCADE"), primary_key=True, index=True
    )
    source: Mapped[str] = mapped_column(String(10), default="curated")  # curated | user


class FetchLog(Base):
    """Last fetch status per (resource, ticker); ticker is '' for universe-wide jobs."""

    __tablename__ = "fetch_log"

    resource: Mapped[str] = mapped_column(String(40), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(12), primary_key=True, default="")
    source: Mapped[str] = mapped_column(String(40))
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20))
    message: Mapped[str | None] = mapped_column(Text)
