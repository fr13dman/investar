from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Company, FetchLog, PriceDaily
from app.services import ingest
from app.services.market_hours import is_market_open
from app.services.refresh import is_refreshing, run_refresh

router = APIRouter(prefix="/api", tags=["admin"])

JOBS = {
    "prices": ("prices_intraday", "yfinance", ingest.refresh_intraday),
    "backfill": ("prices_backfill", "yfinance", ingest.backfill_prices),
    "profiles": ("profiles_all", "yfinance", ingest.enrich_profiles),
    "universe": ("universe", "wikipedia", ingest.load_universe),
}


class RefreshIn(BaseModel):
    scope: Literal["prices", "backfill", "profiles", "universe"] = "prices"


@router.post("/refresh", status_code=202)
def refresh(body: RefreshIn, background: BackgroundTasks):
    resource, source, fn = JOBS[body.scope]
    already = is_refreshing(resource, "")
    if not already:
        background.add_task(run_refresh, resource, "", source, fn)
    return {"scope": body.scope, "started": not already, "refreshing": True}


@router.get("/status")
def status(session: Session = Depends(get_session)):
    logs = session.scalars(select(FetchLog).where(FetchLog.ticker == "")).all()
    return {
        "market_open": is_market_open(),
        "companies": session.scalar(select(func.count()).select_from(Company).where(~Company.is_benchmark)) or 0,
        "price_rows": session.scalar(select(func.count()).select_from(PriceDaily)) or 0,
        "jobs": {
            row.resource: {"fetched_at": row.fetched_at.isoformat(), "status": row.status, "message": row.message,
                           "refreshing": is_refreshing(row.resource, "")}
            for row in logs
        },
        "refreshing": {scope: is_refreshing(res, "") for scope, (res, _, _) in JOBS.items()},
    }
