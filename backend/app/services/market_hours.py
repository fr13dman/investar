from datetime import date, datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas as pd


@lru_cache
def _calendar():
    import exchange_calendars as xcals

    return xcals.get_calendar("XNYS")


def is_market_open(now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    ts = pd.Timestamp(now)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    try:
        return bool(_calendar().is_open_on_minute(ts.floor("min")))
    except Exception:  # outside calendar bounds
        return False


def is_trading_day(day: date | None = None) -> bool:
    day = day or datetime.now(ZoneInfo("America/New_York")).date()
    try:
        return bool(_calendar().is_session(pd.Timestamp(day)))
    except Exception:
        return False
