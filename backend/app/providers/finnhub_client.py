from app import http
from app.config import get_settings
from app.providers.base import ProviderUnavailable

BASE = "https://finnhub.io/api/v1"


class FinnhubNotConfigured(ProviderUnavailable):
    pass


def get(path: str, params: dict) -> object:
    key = get_settings().finnhub_api_key
    if not key:
        raise FinnhubNotConfigured("FINNHUB_API_KEY is not set")
    http.LIMITERS["finnhub"].acquire()
    with http.client() as c:
        # Header auth keeps the key out of access logs.
        r = c.get(f"{BASE}{path}", params=params, headers={"X-Finnhub-Token": key})
        r.raise_for_status()
        return r.json()
