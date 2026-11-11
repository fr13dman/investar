from datetime import date, timedelta
from functools import partial
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models import CeoOverride, CeoScorecard, Company
from app.services import company as company_svc
from app.services.ceo_scorecard import recompute_from_stored, refresh_ceo
from app.services.global_presence import global_payload, refresh_global
from app.services.news import news_payload, refresh_news
from app.services.patents import ensure_assignee_map, patents_payload, refresh_patents, set_assignees
from app.services.refresh import ensure_fresh

router = APIRouter(prefix="/api/companies", tags=["companies"])


def get_company(ticker: str, session: Session = Depends(get_session)) -> Company:
    comp = session.get(Company, ticker.upper())
    if comp is None:
        raise HTTPException(404, f"unknown ticker {ticker}")
    return comp


@router.get("/{ticker}")
def company(background: BackgroundTasks, comp: Company = Depends(get_company), session: Session = Depends(get_session)):
    status = ensure_fresh(session, background, "profile", comp.ticker, "yfinance",
                          timedelta(days=get_settings().filings_ttl_days),
                          partial(company_svc.refresh_profile, ticker=comp.ticker))
    return {**company_svc.profile_payload(session, comp), "refresh": status}


@router.get("/{ticker}/quote")
def quote(comp: Company = Depends(get_company), session: Session = Depends(get_session)):
    return company_svc.live_quote(session, comp.ticker)


@router.get("/{ticker}/prices")
def prices(range: Literal["1d", "1w", "1m", "ytd", "1y", "5y"] = "1y", comp: Company = Depends(get_company),
           session: Session = Depends(get_session)):
    return company_svc.price_series(session, comp.ticker, range)


@router.get("/{ticker}/news")
def news(background: BackgroundTasks, force: bool = False, comp: Company = Depends(get_company),
         session: Session = Depends(get_session)):
    status = ensure_fresh(session, background, "news", comp.ticker, "finnhub",
                          timedelta(minutes=get_settings().news_ttl_minutes),
                          partial(refresh_news, ticker=comp.ticker), force=force)
    return {**news_payload(session, comp.ticker), "refresh": status,
            "configured": bool(get_settings().finnhub_api_key)}


@router.get("/{ticker}/ceo")
def ceo(background: BackgroundTasks, force: bool = False, comp: Company = Depends(get_company),
        session: Session = Depends(get_session)):
    status = ensure_fresh(session, background, "ceo", comp.ticker, "sec+wikidata",
                          timedelta(days=get_settings().filings_ttl_days),
                          partial(refresh_ceo, ticker=comp.ticker), force=force)
    return {"scorecard": company_svc.ceo_payload(session.get(CeoScorecard, comp.ticker)), "refresh": status}


@router.get("/{ticker}/global")
def global_presence(background: BackgroundTasks, force: bool = False, comp: Company = Depends(get_company),
                    session: Session = Depends(get_session)):
    status = ensure_fresh(session, background, "global", comp.ticker, "sec",
                          timedelta(days=get_settings().filings_ttl_days),
                          partial(refresh_global, ticker=comp.ticker), force=force)
    return {**global_payload(session, comp.ticker, comp.cik), "refresh": status}


@router.get("/{ticker}/patents")
def patents(background: BackgroundTasks, force: bool = False, comp: Company = Depends(get_company),
            session: Session = Depends(get_session)):
    ensure_assignee_map(session, comp.ticker)
    status = ensure_fresh(session, background, "patents", comp.ticker, "patentsview",
                          timedelta(days=get_settings().patents_ttl_days),
                          partial(refresh_patents, ticker=comp.ticker), force=force)
    return {**patents_payload(session, comp.ticker), "refresh": status}


class AssigneeIn(BaseModel):
    assignee_name: str
    match: Literal["exact", "prefix"] = "exact"


@router.put("/{ticker}/patent-assignees")
def put_assignees(body: list[AssigneeIn], background: BackgroundTasks, comp: Company = Depends(get_company),
                  session: Session = Depends(get_session)):
    rows = set_assignees(session, comp.ticker, [b.model_dump() for b in body])
    status = ensure_fresh(session, background, "patents", comp.ticker, "patentsview", timedelta(0),
                          partial(refresh_patents, ticker=comp.ticker), force=True)
    return {"assignees": [{"assignee_name": r.assignee_name.strip(), "match": r.match, "source": r.source} for r in rows],
            "refresh": status}


class CeoOverrideIn(BaseModel):
    ceo_name: str | None = None
    tenure_start: date | None = None


@router.put("/{ticker}/ceo")
def set_ceo_override(body: CeoOverrideIn, comp: Company = Depends(get_company), session: Session = Depends(get_session)):
    row = session.get(CeoOverride, comp.ticker) or CeoOverride(ticker=comp.ticker)
    row.ceo_name = (body.ceo_name or "").strip() or None
    row.tenure_start = body.tenure_start
    session.add(row)
    session.commit()
    return {"scorecard": company_svc.ceo_payload(recompute_from_stored(session, comp.ticker))}
