from functools import partial

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Company, MetricsSnapshot
from app.providers.base import ProviderUnavailable
from app.services import tracking
from app.services.niches import niche_tree, set_user_niches
from app.services.refresh import run_refresh
from app.services.screener import row_dict

router = APIRouter(prefix="/api", tags=["niches"])


@router.get("/niches")
def niches(session: Session = Depends(get_session)):
    return niche_tree(session)


@router.get("/search")
def search(q: str = Query(..., min_length=1, max_length=40), limit: int = Query(10, ge=1, le=25),
           session: Session = Depends(get_session)):
    try:
        return tracking.search_market(session, q.strip(), limit)
    except ProviderUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


class TrackIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    niche_ids: list[int] = []


@router.post("/tracked", status_code=202)
def track(body: TrackIn, background: BackgroundTasks, session: Session = Depends(get_session)):
    try:
        comp = tracking.track_symbol(session, body.ticker, body.niche_ids)
    except tracking.TrackError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    background.add_task(run_refresh, tracking.TRACK_RESOURCE, comp.ticker, "yfinance",
                        partial(tracking.backfill_tracked, ticker=comp.ticker))
    return {**row_dict(comp, session.get(MetricsSnapshot, comp.ticker)), "status": "adding"}


@router.get("/tracked/{ticker}/status")
def tracked_status(ticker: str, session: Session = Depends(get_session)):
    return tracking.track_status(session, ticker)


@router.delete("/tracked/{ticker}", status_code=204)
def untrack(ticker: str, session: Session = Depends(get_session)):
    try:
        tracking.untrack(session, ticker)
    except tracking.TrackError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    return Response(status_code=204)


class NichesIn(BaseModel):
    niche_ids: list[int]


@router.put("/companies/{ticker}/niches")
def put_niches(ticker: str, body: NichesIn, session: Session = Depends(get_session)):
    comp = session.get(Company, tracking.normalize(ticker))
    if comp is None:
        raise HTTPException(404, f"unknown ticker {ticker}")
    if comp.extra_source != "user":
        raise HTTPException(409, "niche tags can only be edited on symbols you added")
    try:
        return {"niches": set_user_niches(session, comp.ticker, body.niche_ids)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
