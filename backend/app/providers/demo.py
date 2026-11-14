"""Deterministic offline providers for market search, profiles and prices (OFFLINE_PROVIDERS=true)."""

import random
import zlib
from datetime import date

from app.providers.base import PriceBar, Profile, SymbolMatch

DEMO_PROFILES = {
    "NBIS": Profile("NBIS", sector="Communication Services", industry="Internet Content & Information",
                    exchange="NMS", name="Nebius Group N.V.", quote_type="EQUITY", currency="USD",
                    shares_outstanding=2.4e8, country="Netherlands",
                    description="Nebius builds full-stack AI cloud infrastructure (demo profile)."),
    "IONQ": Profile("IONQ", sector="Technology", industry="Computer Hardware", exchange="NYQ", name="IonQ, Inc.",
                    quote_type="EQUITY", currency="USD", shares_outstanding=2.6e8, country="United States"),
    "NLR": Profile("NLR", exchange="PCX", name="VanEck Uranium and Nuclear ETF", quote_type="ETF", currency="USD",
                   shares_outstanding=2.5e7),
}
DEMO_MATCHES = [
    SymbolMatch("NBIS", "Nebius Group N.V.", "NMS", "EQUITY"),
    SymbolMatch("YDX.DE", "Nebius Group N.V.", "GER", "EQUITY"),
    SymbolMatch("IONQ", "IonQ, Inc.", "NYQ", "EQUITY"),
    SymbolMatch("NLR", "VanEck Uranium and Nuclear ETF", "PCX", "ETF"),
    SymbolMatch("URA", "Global X Uranium ETF", "PCX", "ETF"),
    SymbolMatch("NVDA", "NVIDIA Corporation", "NMS", "EQUITY"),
]


class DemoSearch:
    def search(self, query: str, limit: int = 10) -> list[SymbolMatch]:
        q = query.strip().lower()
        return [m for m in DEMO_MATCHES if q in m.symbol.lower() or q in (m.name or "").lower()][:limit]


class DemoProfiles:
    def profile(self, ticker: str) -> Profile | None:
        return DEMO_PROFILES.get(ticker)


class DemoPrices:
    def history(self, tickers: list[str], period: str = "5y") -> list[PriceBar]:
        from app.seed import _series, _trading_days

        days = _trading_days(date.today(), 252 * 2)
        bars = []
        for t in tickers:
            rng = random.Random(zlib.crc32(t.encode()))
            for d, c in _series(rng, days, rng.uniform(10, 120), rng.uniform(-0.0005, 0.002)):
                bars.append(PriceBar(t, d, close=c, open=c, high=round(c * 1.01, 2), low=round(c * 0.99, 2),
                                     adj_close=c, volume=float(rng.randint(1_000_000, 9_000_000))))
        return bars

    def recent(self, tickers: list[str]) -> list[PriceBar]:
        return [b for b in self.history(tickers) if (date.today() - b.date).days <= 7]

    def splits(self, ticker: str) -> list[tuple]:
        return []

    def intraday(self, ticker: str, period: str, interval: str) -> list[dict]:
        return []


class DemoConstituents:
    def ciks(self) -> dict[str, str]:
        return {}

    def fetch(self) -> list:
        return []
