import logging
from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app import db
from app.config import get_settings
from app.services import ingest
from app.services.market_hours import is_market_open, is_trading_day

log = logging.getLogger(__name__)
NY = "America/New_York"

def _weekly_research(session) -> None:
    from app.services.research_jobs import refresh_all_research

    refresh_all_research(session)


WEEKLY_HOOKS: list[Callable] = [_weekly_research]


def _with_session(fn: Callable) -> None:
    session = db.SessionLocal()
    try:
        fn(session)
    except Exception:
        log.exception("scheduled job %s failed", getattr(fn, "__name__", fn))
    finally:
        session.close()


def intraday_job() -> None:
    if is_market_open():
        _with_session(ingest.refresh_intraday)


def eod_job() -> None:
    if is_trading_day():
        _with_session(ingest.refresh_intraday)


def weekly_job() -> None:
    _with_session(ingest.load_universe)
    _with_session(ingest.enrich_profiles)
    for hook in WEEKLY_HOOKS:
        _with_session(hook)


def build_scheduler() -> BackgroundScheduler:
    s = BackgroundScheduler(timezone=NY)
    minutes = get_settings().intraday_interval_minutes
    s.add_job(intraday_job, IntervalTrigger(minutes=minutes), id="intraday", max_instances=1, coalesce=True)
    s.add_job(eod_job, CronTrigger(day_of_week="mon-fri", hour=16, minute=20, timezone=NY), id="eod",
              max_instances=1, coalesce=True)
    s.add_job(weekly_job, CronTrigger(day_of_week="sun", hour=2, minute=0, timezone=NY), id="weekly",
              max_instances=1, coalesce=True)
    return s
