import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Company
from app.services import etfs as svc

router = APIRouter(prefix="/api/etfs", tags=["etfs"])

_TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,11}$")
MAX_REFRESH = 25


def _require_etf(session: Session, ticker: str) -> str:
    t = ticker.strip().upper()
    if not _TICKER_RE.match(t):
        raise HTTPException(422, f"invalid ticker '{ticker}'")
    comp = session.get(Company, t)
    if not comp or comp.asset_type != "etf":
        raise HTTPException(404, f"unknown ETF '{t}'")
    return t


class RefreshBody(BaseModel):
    tickers: list[str] = Field(default_factory=list, max_length=MAX_REFRESH)

    @field_validator("tickers")
    @classmethod
    def _normalize(cls, values: list[str]) -> list[str]:
        out: list[str] = []
        for raw in values[:MAX_REFRESH]:
            t = raw.strip().upper()
            if not t:
                continue
            if not _TICKER_RE.match(t):
                raise ValueError(f"invalid ticker '{raw}'")
            out.append(t)
        return out


@router.get("")
def list_etfs(
    niche: str | None = None,
    period: str = Query("wow", pattern="^(wow|mom|yoy)$"),
    session: Session = Depends(get_session),
):
    try:
        return svc.list_niche_etfs(session, niche=niche, period=period)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/vistashares")
def vistashares(
    family: str | None = None,
    period: str = Query("wow", pattern="^(wow|mom|yoy)$"),
    session: Session = Depends(get_session),
):
    try:
        return svc.list_vistashares(session, family=family, period=period)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{ticker}/heatmap")
def heatmap(
    ticker: str,
    period: str = Query("wow", pattern="^(wow|mom|yoy)$"),
    session: Session = Depends(get_session),
):
    t = _require_etf(session, ticker)
    try:
        return svc.fund_heatmap(session, t, period=period)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/refresh")
def refresh_many(body: RefreshBody, session: Session = Depends(get_session)):
    known = []
    for t in body.tickers:
        comp = session.get(Company, t)
        if comp and comp.asset_type == "etf":
            known.append(t)
    return svc.refresh_etfs(session, known)


@router.post("/{ticker}/refresh")
def refresh_one(ticker: str, session: Session = Depends(get_session)):
    t = _require_etf(session, ticker)
    return svc.refresh_etfs(session, [t])
