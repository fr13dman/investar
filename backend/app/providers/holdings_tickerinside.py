"""TickerInside free ETF holdings API for non-VistaShares curated funds."""

from datetime import date, datetime

import httpx

from app.providers.base import FundHoldings, HoldingLine, ProviderUnavailable
from app.providers.holdings_vistashares import classify_kind

BASE = "https://tickerinside.com/api/v1"


def _normalize_weights(raw: dict) -> dict[str, float]:
    parsed: dict[str, float] = {}
    for sym, weight in raw.items():
        try:
            parsed[str(sym)] = float(weight)
        except (TypeError, ValueError):
            continue
    total = sum(parsed.values())
    if total <= 1.5:
        return {k: v * 100 for k, v in parsed.items()}
    return parsed


def parse_fund_json(ticker: str, data: dict) -> FundHoldings:
    raw = data.get("holdings") or {}
    lines: list[HoldingLine] = []
    if isinstance(raw, dict):
        for sym, weight in _normalize_weights(raw).items():
            sym_s = sym.strip().upper().replace(".", "-") if sym else None
            lines.append(HoldingLine(ticker=sym_s, name=None, weight_pct=weight, kind=classify_kind(sym_s, None)))
    as_of = None
    for key in ("holdings_as_of", "as_of"):
        val = data.get(key)
        if isinstance(val, str):
            for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
                try:
                    as_of = datetime.strptime(val[:10], fmt).date()
                    break
                except ValueError:
                    continue
        if as_of:
            break
    aum = None
    if data.get("aum_b") is not None:
        try:
            aum = float(data["aum_b"]) * 1e9
        except (TypeError, ValueError):
            aum = None
    return FundHoldings(ticker=ticker.upper(), as_of=as_of or date.today(), source="tickerinside",
                        holdings=lines, aum=aum)


class TickerInsideHoldings:
    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def holdings(self, ticker: str) -> FundHoldings | None:
        t = ticker.strip().upper()
        try:
            r = httpx.get(f"{BASE}/fund/{t.lower()}.json", timeout=self.timeout, follow_redirects=True)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return parse_fund_json(t, r.json())
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderUnavailable(f"TickerInside {t}: {exc}") from exc
