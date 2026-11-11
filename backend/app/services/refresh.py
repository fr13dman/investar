"""Freshness tracking (fetch_log) and de-duplicated background refreshes.

Research endpoints return what is stored immediately; if the data is older than its TTL
they schedule a background refresh and report `refreshing=True` so the UI can poll."""

import logging
import threading
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import db
from app.models import FetchLog
from app.providers.base import ProviderUnavailable

log = logging.getLogger(__name__)

_inflight: set[tuple[str, str]] = set()
_lock = threading.Lock()


def record_fetch(session: Session, resource: str, ticker: str, source: str, status: str = "ok",
                 message: str | None = None) -> None:
    row = session.get(FetchLog, (resource, ticker or ""))
    if row is None:
        row = FetchLog(resource=resource, ticker=ticker or "")
        session.add(row)
    row.source = source
    row.status = status
    row.message = message
    row.fetched_at = datetime.now()
    session.commit()


def last_fetch(session: Session, resource: str, ticker: str = "") -> FetchLog | None:
    return session.get(FetchLog, (resource, ticker or ""))


def is_stale(session: Session, resource: str, ticker: str, ttl: timedelta) -> bool:
    row = last_fetch(session, resource, ticker)
    if row is None:
        return True
    # Retry failures sooner than the full TTL.
    effective = ttl if row.status == "ok" else min(ttl, timedelta(minutes=10))
    return datetime.now() - row.fetched_at > effective


def is_refreshing(resource: str, ticker: str) -> bool:
    with _lock:
        return (resource, ticker) in _inflight


def run_refresh(resource: str, ticker: str, source: str, fn: Callable[[Session], None]) -> None:
    """Run `fn` with its own session, recording success/failure. Skips if already running."""
    key = (resource, ticker)
    with _lock:
        if key in _inflight:
            return
        _inflight.add(key)
    session = db.SessionLocal()
    try:
        fn(session)
        record_fetch(session, resource, ticker, source, "ok")
    except ProviderUnavailable as exc:
        log.warning("refresh %s/%s skipped: %s", resource, ticker, exc)
        session.rollback()
        record_fetch(session, resource, ticker, source, "error", str(exc)[:500])
    except Exception as exc:  # noqa: BLE001
        log.exception("refresh %s/%s failed", resource, ticker)
        session.rollback()
        record_fetch(session, resource, ticker, source, "error", str(exc)[:500])
    finally:
        session.close()
        with _lock:
            _inflight.discard(key)


def ensure_fresh(session: Session, background, resource: str, ticker: str, source: str, ttl: timedelta,
                 fn: Callable[[Session], None], force: bool = False) -> dict:
    """Schedule `fn` on FastAPI BackgroundTasks when stale. Returns status for the response."""
    stale = force or is_stale(session, resource, ticker, ttl)
    if stale and not is_refreshing(resource, ticker):
        background.add_task(run_refresh, resource, ticker, source, fn)
        refreshing = True
    else:
        refreshing = is_refreshing(resource, ticker)
    row = last_fetch(session, resource, ticker)
    return {
        "fetched_at": row.fetched_at.isoformat() if row else None,
        "status": row.status if row else None,
        "message": row.message if row else None,
        "refreshing": refreshing,
    }
