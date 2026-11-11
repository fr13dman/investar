from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Company, Watchlist, WatchlistItem

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])


class WatchlistIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ItemIn(BaseModel):
    ticker: str


def _out(session: Session, w: Watchlist) -> dict:
    tickers = list(session.scalars(select(WatchlistItem.ticker).where(WatchlistItem.watchlist_id == w.id)
                                   .order_by(WatchlistItem.ticker)))
    return {"id": w.id, "name": w.name, "tickers": tickers}


def _get(session: Session, wid: int) -> Watchlist:
    w = session.get(Watchlist, wid)
    if w is None:
        raise HTTPException(404, "watchlist not found")
    return w


@router.get("")
def list_watchlists(session: Session = Depends(get_session)):
    return [_out(session, w) for w in session.scalars(select(Watchlist).order_by(func.lower(Watchlist.name)))]


@router.post("", status_code=201)
def create_watchlist(body: WatchlistIn, session: Session = Depends(get_session)):
    w = Watchlist(name=body.name.strip())
    session.add(w)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "a watchlist with that name already exists") from exc
    return _out(session, w)


@router.put("/{wid}")
def rename_watchlist(wid: int, body: WatchlistIn, session: Session = Depends(get_session)):
    w = _get(session, wid)
    w.name = body.name.strip()
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "a watchlist with that name already exists") from exc
    return _out(session, w)


@router.delete("/{wid}", status_code=204)
def delete_watchlist(wid: int, session: Session = Depends(get_session)):
    session.delete(_get(session, wid))
    session.commit()


@router.post("/{wid}/items", status_code=201)
def add_item(wid: int, body: ItemIn, session: Session = Depends(get_session)):
    w = _get(session, wid)
    ticker = body.ticker.strip().upper()
    if session.get(Company, ticker) is None:
        raise HTTPException(404, "unknown ticker")
    if session.get(WatchlistItem, (wid, ticker)) is None:
        session.add(WatchlistItem(watchlist_id=wid, ticker=ticker))
        session.commit()
    return _out(session, w)


@router.delete("/{wid}/items/{ticker}")
def remove_item(wid: int, ticker: str, session: Session = Depends(get_session)):
    w = _get(session, wid)
    session.execute(delete(WatchlistItem).where(WatchlistItem.watchlist_id == wid,
                                                WatchlistItem.ticker == ticker.upper()))
    session.commit()
    return _out(session, w)
