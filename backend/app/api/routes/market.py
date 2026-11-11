from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.services import screener

router = APIRouter(prefix="/api", tags=["market"])

SortKey = Literal["ticker", "name", "sector", "industry", "price", "market_cap", "volume", "pe_ratio",
                  "chg_1d", "chg_1w", "chg_ytd"]


@router.get("/sectors")
def sectors(session: Session = Depends(get_session)):
    return screener.sector_tree(session)


@router.get("/stocks")
def stocks(
    sector: str | None = None,
    industry: str | None = None,
    index: Literal["all", "sp500", "ndx100", "both"] = "all",
    cap_band: Literal["mega", "large", "mid", "small"] | None = None,
    q: str | None = None,
    watchlist_id: int | None = None,
    sort: SortKey = "market_cap",
    order: Literal["asc", "desc"] = "desc",
    mode: Literal["pct", "abs"] = "pct",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=600),
    session: Session = Depends(get_session),
):
    query = screener.ScreenerQuery(sector=sector, industry=industry, index=index, cap_band=cap_band, q=q,
                                   watchlist_id=watchlist_id, sort=sort, order=order, mode=mode, page=page,
                                   page_size=page_size)
    try:
        return screener.screen(session, query)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/movers")
def movers(
    sector: str | None = None,
    industry: str | None = None,
    window: Literal["chg_1d", "chg_1w", "chg_ytd"] = "chg_1d",
    mode: Literal["pct", "abs"] = "pct",
    limit: int = Query(5, ge=1, le=25),
    session: Session = Depends(get_session),
):
    return screener.movers(session, sector=sector, industry=industry, window=window, mode=mode, limit=limit)


@router.get("/benchmarks")
def benchmarks(session: Session = Depends(get_session)):
    return screener.benchmarks(session)
