from datetime import date, datetime

from app.providers import finnhub_client
from app.providers.base import NewsItem, to_dotted


def parse_news(payload: list[dict]) -> list[NewsItem]:
    items, seen = [], set()
    for a in payload or []:
        url, headline = a.get("url"), (a.get("headline") or "").strip()
        if not url or not headline or url in seen:
            continue
        seen.add(url)
        ts = a.get("datetime")
        items.append(
            NewsItem(
                external_id=str(a["id"]) if a.get("id") is not None else None,
                headline=headline,
                summary=(a.get("summary") or "").strip() or None,
                source=a.get("source"),
                url=url,
                image=a.get("image") or None,
                published_at=datetime.fromtimestamp(ts) if ts else datetime.now(),
            )
        )
    return items


class FinnhubNews:
    def company_news(self, ticker: str, start: date, end: date) -> list[NewsItem]:
        payload = finnhub_client.get(
            "/company-news", {"symbol": to_dotted(ticker), "from": start.isoformat(), "to": end.isoformat()}
        )
        return parse_news(payload)  # type: ignore[arg-type]
