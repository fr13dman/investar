from datetime import datetime, timedelta, timezone

from app.models import FetchLog
from app.services import refresh
from app.services.market_hours import is_market_open, is_trading_day


def test_staleness_and_error_retry(session):
    assert refresh.is_stale(session, "news", "AAPL", timedelta(hours=1))
    refresh.record_fetch(session, "news", "AAPL", "finnhub")
    assert not refresh.is_stale(session, "news", "AAPL", timedelta(hours=1))
    row = session.get(FetchLog, ("news", "AAPL"))
    row.status = "error"
    row.fetched_at = datetime.now() - timedelta(minutes=15)
    session.commit()
    # errors retry after 10 minutes even with a long TTL
    assert refresh.is_stale(session, "news", "AAPL", timedelta(days=7))


def test_run_refresh_records_failure(session):
    def boom(_s):
        raise RuntimeError("provider down")

    refresh.run_refresh("ceo", "AAPL", "sec", boom)
    session.expire_all()
    row = session.get(FetchLog, ("ceo", "AAPL"))
    assert row.status == "error" and "provider down" in row.message
    assert not refresh.is_refreshing("ceo", "AAPL")


def test_ensure_fresh_schedules_once(session):
    class Tasks:
        def __init__(self):
            self.calls = []

        def add_task(self, fn, *args):
            self.calls.append((fn, args))

    tasks = Tasks()
    status = refresh.ensure_fresh(session, tasks, "news", "MSFT", "finnhub", timedelta(hours=1), lambda s: None)
    assert status["refreshing"] is True and len(tasks.calls) == 1
    refresh.record_fetch(session, "news", "MSFT", "finnhub")
    status = refresh.ensure_fresh(session, tasks, "news", "MSFT", "finnhub", timedelta(hours=1), lambda s: None)
    assert status["refreshing"] is False and len(tasks.calls) == 1


def test_market_hours():
    # Tue Nov 10 2026 15:00 UTC = 10:00 ET (open); 22:00 UTC = 17:00 ET (closed)
    assert is_market_open(datetime(2026, 11, 10, 15, 0, tzinfo=timezone.utc))
    assert not is_market_open(datetime(2026, 11, 10, 22, 0, tzinfo=timezone.utc))
    # Thanksgiving 2026 (Nov 26) is a holiday; Saturday is not a session.
    assert not is_trading_day(datetime(2026, 11, 26).date())
    assert not is_trading_day(datetime(2026, 11, 14).date())
    assert is_trading_day(datetime(2026, 11, 10).date())


def test_scheduler_jobs_registered():
    from app.scheduler import build_scheduler

    s = build_scheduler()
    assert {j.id for j in s.get_jobs()} == {"intraday", "eod", "weekly"}
