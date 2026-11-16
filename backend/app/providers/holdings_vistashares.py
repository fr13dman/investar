"""VistaShares issuer holdings CSV + optional fund data.json for AUM."""

import csv
import io
import json
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
    text = str(raw).replace(",", "").strip()
    # Accounting negatives like "(1.5)" for written calls.
    neg = text.startswith("(") and text.endswith(")")
    if neg:
        text = text[1:-1]
    m = _WEIGHT_RE.search(text)
    if not m:
        return None
    value = float(m.group())
    if neg or text.lstrip().startswith("-"):
        return -abs(value)
    return value


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


_SUFFIX = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}
_OTHER_NAME = re.compile(r"\b(cash|option|options|call|calls|put|puts|overlay|overlays)\b", re.I)


def parse_money(raw: str | float | int | None) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().replace(",", "").replace("$", "")
    if not text:
        return None
    mult = 1.0
    if text[-1].lower() in _SUFFIX:
        mult = _SUFFIX[text[-1].lower()]
        text = text[:-1].strip()
    try:
        return float(text) * mult
    except ValueError:
        digits = re.sub(r"[^\d.]", "", text)
        return float(digits) * mult if digits else None


def classify_kind(ticker: str | None, name: str | None) -> str:
    t = (ticker or "").upper()
    n = (name or "").lower()
    if not t or t in {"CASH", "USD", "-"} or _OTHER_NAME.search(n):
        return "other"
    # Foreign listings with spaces (e.g. "000660 KS") still count as equity for allocation maps.
    return "equity"


def parse_holdings_csv(ticker: str, text: str) -> FundHoldings:
    if "<html" in text[:500].lower():
        raise ProviderUnavailable(f"VistaShares holdings for {ticker} returned HTML, not CSV")
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = {f.lower() for f in (reader.fieldnames or [])}
    if not fieldnames or not ({"weight", "weight_pct", "%"} & fieldnames or "ticker" in fieldnames or "symbol" in fieldnames):
        raise ProviderUnavailable(f"VistaShares holdings for {ticker} missing expected CSV columns")
    by_key: dict[str, HoldingLine] = {}
    as_of: date | None = None
    for row in reader:
        as_of = as_of or parse_as_of(row.get("as_of") or row.get("date"))
        name = (row.get("name") or row.get("security") or "").strip() or None
        sym = (row.get("ticker") or row.get("symbol") or "").strip() or None
        weight = parse_weight(row.get("weight") or row.get("weight_pct") or row.get("%"))
        if weight is None:
            continue
        kind = classify_kind(sym, name)
        key = (sym.upper().replace(".", "-") if sym else f"OTHER:{name or '?'}") + f":{kind}"
        if key in by_key:
            by_key[key].weight_pct += weight
        else:
            by_key[key] = HoldingLine(
                ticker=sym.upper().replace(".", "-") if sym else None,
                name=name,
                weight_pct=weight,
                kind=kind,
            )
    lines = list(by_key.values())
    if not lines:
        raise ProviderUnavailable(f"VistaShares holdings for {ticker} were empty")
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
            meta = json.loads(self._get(f"/etf/{t.lower()}/data.json"))
            fund.aum = parse_money(meta.get("net_assets") or meta.get("aum"))
            if not fund.as_of:
                fund.as_of = parse_as_of(meta.get("net_assets_as_of") or meta.get("as_of"))
        except (ProviderUnavailable, ValueError, TypeError, json.JSONDecodeError):
            pass
        return fund
