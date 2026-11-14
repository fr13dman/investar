"""Symbol search across the whole market via Yahoo Finance's search endpoint (yfinance.Search)."""

from app.providers.base import ProviderUnavailable, SymbolMatch
from app.providers.prices_yfinance import _yf


def parse_search(quotes: list[dict]) -> list[SymbolMatch]:
    out = []
    for q in quotes or []:
        symbol = q.get("symbol")
        if not symbol:
            continue
        out.append(SymbolMatch(symbol=symbol, name=q.get("longname") or q.get("shortname"),
                               exchange=q.get("exchange"), quote_type=q.get("quoteType")))
    return out


class YFinanceSearch:
    def search(self, query: str, limit: int = 10) -> list[SymbolMatch]:
        try:
            s = _yf().Search(query, max_results=limit, news_count=0, lists_count=0, recommended=0,
                             include_cb=False, raise_errors=True)
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailable(f"Yahoo search failed: {exc}") from exc
        return parse_search(s.quotes)
