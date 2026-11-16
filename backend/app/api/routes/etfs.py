from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.services import etfs as svc

router = APIRouter(prefix="/api/etfs", tags=["etfs"])


class RefreshBody(BaseModel):
    tickers: list[str]


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
    try:
        return svc.fund_heatmap(session, ticker, period=period)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/refresh")
def refresh_many(body: RefreshBody, session: Session = Depends(get_session)):
    return svc.refresh_etfs(session, body.tickers)


@router.post("/{ticker}/refresh")
def refresh_one(ticker: str, session: Session = Depends(get_session)):
    return svc.refresh_etfs(session, [ticker])
