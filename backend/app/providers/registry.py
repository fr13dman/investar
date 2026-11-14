"""Single place to choose concrete providers. Tests call `override(...)` to inject fakes."""

from typing import Any

_overrides: dict[str, Any] = {}


def override(**providers: Any) -> None:
    _overrides.update(providers)


def reset() -> None:
    _overrides.clear()


def _offline() -> bool:
    from app.config import get_settings

    return get_settings().offline_providers


def constituents():
    if "constituents" in _overrides:
        return _overrides["constituents"]
    if _offline():
        from app.providers.demo import DemoConstituents

        return DemoConstituents()
    from app.providers.constituents import WikipediaConstituents

    return WikipediaConstituents()


def prices():
    if "prices" in _overrides:
        return _overrides["prices"]
    if _offline():
        from app.providers.demo import DemoPrices

        return DemoPrices()
    from app.providers.prices_yfinance import YFinancePrices

    return YFinancePrices()


def profiles():
    if "profiles" in _overrides:
        return _overrides["profiles"]
    if _offline():
        from app.providers.demo import DemoProfiles

        return DemoProfiles()
    from app.providers.prices_yfinance import YFinanceProfiles

    return YFinanceProfiles()


def search():
    if "search" in _overrides:
        return _overrides["search"]
    if _offline():
        from app.providers.demo import DemoSearch

        return DemoSearch()
    from app.providers.search_yfinance import YFinanceSearch

    return YFinanceSearch()


def quotes():
    if "quotes" in _overrides:
        return _overrides["quotes"]
    from app.providers.quotes_finnhub import FinnhubQuotes

    return FinnhubQuotes()


def news():
    if "news" in _overrides:
        return _overrides["news"]
    from app.providers.news_finnhub import FinnhubNews

    return FinnhubNews()


def sec():
    if "sec" in _overrides:
        return _overrides["sec"]
    from app.providers.sec_edgar import SecEdgar

    return SecEdgar()


def wikidata():
    if "wikidata" in _overrides:
        return _overrides["wikidata"]
    from app.providers.wikidata import Wikidata

    return Wikidata()


def patents():
    if "patents" in _overrides:
        return _overrides["patents"]
    from app.providers.patents_patentsview import PatentsViewApi

    return PatentsViewApi()
