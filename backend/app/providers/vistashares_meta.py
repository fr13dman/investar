"""VistaShares /funds.json for AUM and fund facts without requiring local companies."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import httpx

from app.providers.base import ProviderUnavailable
from app.providers.holdings_vistashares import parse_money

log = logging.getLogger(__name__)
FUNDS_URL = "https://www.vistashares.com/funds.json"


@dataclass
class FundMeta:
    ticker: str
    name: str | None
    aum: float | None
    family: str | None = None


def parse_funds_json(data: dict) -> dict[str, FundMeta]:
    out: dict[str, FundMeta] = {}
    for row in data.get("funds") or []:
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        out[ticker] = FundMeta(
            ticker=ticker,
            name=row.get("name"),
            aum=parse_money(row.get("net_assets") or row.get("aum")),
            family=row.get("family"),
        )
    return out


# Fallback AUMs when offline / issuer unreachable (approx, for maps).
DEMO_META: dict[str, FundMeta] = {
    "OMAH": FundMeta("OMAH", None, 1.12e9),
    "ACKY": FundMeta("ACKY", None, 4.2e7),
    "DRKY": FundMeta("DRKY", None, 1.8e7),
    "TPRY": FundMeta("TPRY", None, 3.3e6),
    "SIOO": FundMeta("SIOO", None, 2.2e7),
    "QUSA": FundMeta("QUSA", None, 2.2e7),
    "AIS": FundMeta("AIS", None, 1.08e9),
    "POW": FundMeta("POW", None, 6.3e7),
    "GALX": FundMeta("GALX", None, 3.0e6),
    "RTOO": FundMeta("RTOO", None, 3.6e6),
    "AMMO": FundMeta("AMMO", None, 2.7e6),
    "VOOB": FundMeta("VOOB", None, 2.0e7),
    "QQQB": FundMeta("QQQB", None, 1.5e7),
}


def fetch_fund_meta(timeout: float = 20.0) -> dict[str, FundMeta]:
    from app.config import get_settings

    if get_settings().offline_providers:
        return dict(DEMO_META)
    try:
        r = httpx.get(FUNDS_URL, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        return parse_funds_json(r.json())
    except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError) as exc:
        log.warning("VistaShares funds.json unavailable: %s", exc)
        return dict(DEMO_META)
