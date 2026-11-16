"""VistaShares issuer holdings CSV + optional fund data.json for AUM."""

import csv
import io
import re
from datetime import date, datetime

import httpx

from app.providers.base import FundHoldings, HoldingLine, ProviderUnavailable

BASE = "https://www.vistashares.com"
_WEIGHT_RE = re.compile(r"[-+]?\d*\.?\d+")
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def parse_weight(raw: str | float | int | None) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    m = _WEIGHT_RE.search(str(raw).replace(",", ""))
    return float(m.group()) if m else None


def parse_as_of(raw: str | None) -> date | None:
    if not raw:
        return None
    text = raw.strip().strip('"')
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    # "November 13, 2026"
    parts = re.split(r"[,\s]+", text)
    if len(parts) >= 3 and parts[0].lower() in _MONTHS:
        try:
            return date(int(parts[2]), _MONTHS[parts[0].lower()], int(parts[1]))
        except (ValueError, KeyError):
            return None
    return None


def parse_money(raw: str | float | int | None) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    digits = re.sub(r"[^\d.]", "", str(raw))
    return float(digits) if digits else None


def classify_kind(ticker: str | None, name: str | None) -> str:
    t = (ticker or "").upper()
    n = (name or "").lower()
    if not t or t in {"CASH", "USD", "-"} or "cash" in n or "option" in n or "call" in n or "put " in n:
        return "other"
    # Foreign listings with spaces (e.g. "000660 KS") still count as equity for allocation maps.
    return "equity"


def parse_holdings_csv(ticker: str, text: str) -> FundHoldings:
    reader = csv.DictReader(io.StringIO(text))
    lines: list[HoldingLine] = []
    as_of: date | None = None
    for row in reader:
        as_of = as_of or parse_as_of(row.get("as_of") or row.get("date"))
        name = (row.get("name") or row.get("security") or "").strip() or None
        sym = (row.get("ticker") or row.get("symbol") or "").strip() or None
        weight = parse_weight(row.get("weight") or row.get("weight_pct") or row.get("%"))
        if weight is None:
            continue
        kind = classify_kind(sym, name)
        lines.append(HoldingLine(ticker=sym.upper().replace(".", "-") if sym else None, name=name,
                                 weight_pct=weight, kind=kind))
    return FundHoldings(ticker=ticker.upper(), as_of=as_of, source="vistashares", holdings=lines)


class VistaSharesHoldings:
    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def _get(self, path: str) -> str:
        try:
            r = httpx.get(f"{BASE}{path}", timeout=self.timeout, follow_redirects=True)
            r.raise_for_status()
            return r.text
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"VistaShares {path}: {exc}") from exc

    def holdings(self, ticker: str) -> FundHoldings | None:
        t = ticker.strip().upper()
        fund = parse_holdings_csv(t, self._get(f"/etf/{t.lower()}/holdings.csv"))
        try:
            import json

            meta = json.loads(self._get(f"/etf/{t.lower()}/data.json"))
            fund.aum = parse_money(meta.get("net_assets") or meta.get("aum"))
            if not fund.as_of:
                fund.as_of = parse_as_of(meta.get("net_assets_as_of") or meta.get("as_of"))
        except (ProviderUnavailable, ValueError, TypeError):
            pass
        return fund
