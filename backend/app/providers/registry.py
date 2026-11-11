"""Single place to choose concrete providers. Tests call `override(...)` to inject fakes."""

from typing import Any

_overrides: dict[str, Any] = {}


def override(**providers: Any) -> None:
    _overrides.update(providers)


def reset() -> None:
    _overrides.clear()


def constituents():
    if "constituents" in _overrides:
        return _overrides["constituents"]
    from app.providers.constituents import WikipediaConstituents

    return WikipediaConstituents()


def prices():
    if "prices" in _overrides:
        return _overrides["prices"]
    from app.providers.prices_yfinance import YFinancePrices

    return YFinancePrices()


def profiles():
    if "profiles" in _overrides:
        return _overrides["profiles"]
    from app.providers.prices_yfinance import YFinanceProfiles

    return YFinanceProfiles()


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
