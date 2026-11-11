from datetime import datetime

from app.providers import finnhub_client
from app.providers.base import Quote, to_dotted


def parse_quote(ticker: str, payload: dict) -> Quote | None:
    """Finnhub /quote: c=current, pc=previous close, h/l=day range, t=unix time. Unknown symbols return zeros."""
    price = payload.get("c")
    if not price:
        return None
    ts = payload.get("t")
    return Quote(
        ticker=ticker,
        price=float(price),
        prev_close=float(payload["pc"]) if payload.get("pc") else None,
        day_high=float(payload["h"]) if payload.get("h") else None,
        day_low=float(payload["l"]) if payload.get("l") else None,
        as_of=datetime.fromtimestamp(ts) if ts else datetime.now(),
    )


class FinnhubQuotes:
    def quote(self, ticker: str) -> Quote | None:
        return parse_quote(ticker, finnhub_client.get("/quote", {"symbol": to_dotted(ticker)}))  # type: ignore[arg-type]
