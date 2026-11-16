"""Deterministic offline holdings for demo / Playwright."""

from datetime import date

from app.providers.base import FundHoldings, HoldingLine

# Synthetic top holdings; weights sum near 100 with an Other residual.
DEMO_HOLDINGS: dict[str, list[tuple[str | None, str, float, str]]] = {
    "URA": [
        ("CCJ", "Cameco", 18.0, "equity"),
        ("UEC", "Uranium Energy", 8.5, "equity"),
        ("NXE", "NexGen Energy", 7.2, "equity"),
        ("DNN", "Denison Mines", 5.1, "equity"),
        ("UUUU", "Energy Fuels", 4.8, "equity"),
        (None, "Cash and other", 56.4, "other"),
    ],
    "AIS": [
        ("MU", "Micron Technology", 7.3, "equity"),
        ("AMD", "Advanced Micro Devices", 7.0, "equity"),
        ("TSM", "Taiwan Semiconductor", 4.4, "equity"),
        ("NVDA", "NVIDIA", 2.0, "equity"),
        ("VRT", "Vertiv", 3.4, "equity"),
        ("MRVL", "Marvell", 3.4, "equity"),
        ("ANET", "Arista", 2.6, "equity"),
        (None, "Cash and other", 69.9, "other"),
    ],
    "POW": [
        ("ETN", "Eaton", 4.8, "equity"),
        ("GEV", "GE Vernova", 3.4, "equity"),
        ("AEP", "American Electric Power", 3.4, "equity"),
        ("NVDA", "NVIDIA", 2.1, "equity"),
        (None, "Cash and other", 86.3, "other"),
    ],
    "OMAH": [
        ("AAPL", "Apple", 8.0, "equity"),
        ("AMZN", "Amazon", 7.5, "equity"),
        ("AXP", "American Express", 6.0, "equity"),
        ("KO", "Coca-Cola", 5.5, "equity"),
        (None, "Options and cash", 73.0, "other"),
    ],
    "VOOB": [
        ("AAPL", "Apple", 7.0, "equity"),
        ("MSFT", "Microsoft", 6.5, "equity"),
        ("NVDA", "NVIDIA", 5.0, "equity"),
        (None, "Overlays and cash", 81.5, "other"),
    ],
    "RTOO": [
        ("ISRG", "Intuitive Surgical", 6.0, "equity"),
        ("ROK", "Rockwell Automation", 5.0, "equity"),
        ("TSLA", "Tesla", 4.0, "equity"),
        (None, "Cash and other", 85.0, "other"),
    ],
    "GALX": [
        ("RKLB", "Rocket Lab", 5.0, "equity"),
        ("ASTS", "AST SpaceMobile", 4.0, "equity"),
        (None, "Cash and other", 91.0, "other"),
    ],
    "AMMO": [
        ("LMT", "Lockheed Martin", 6.0, "equity"),
        ("RTX", "RTX", 5.5, "equity"),
        (None, "Cash and other", 88.5, "other"),
    ],
}

# Approximate demo AUMs (USD).
DEMO_AUM = {
    "URA": 4.7e9,
    "AIS": 1.08e9,
    "POW": 6.3e7,
    "OMAH": 1.12e9,
    "VOOB": 2e7,
    "RTOO": 3.6e6,
    "GALX": 3e6,
    "AMMO": 2.7e6,
}


class DemoHoldings:
    def holdings(self, ticker: str) -> FundHoldings | None:
        t = ticker.strip().upper()
        rows = DEMO_HOLDINGS.get(t)
        if not rows:
            # Generic stub so any curated ETF still renders a map offline.
            rows = [
                ("AAPL", "Apple", 10.0, "equity"),
                ("MSFT", "Microsoft", 9.0, "equity"),
                ("NVDA", "NVIDIA", 8.0, "equity"),
                (None, "Cash and other", 73.0, "other"),
            ]
        return FundHoldings(
            ticker=t,
            as_of=date.today(),
            source="demo",
            aum=DEMO_AUM.get(t, 5e7),
            holdings=[HoldingLine(ticker=sym, name=name, weight_pct=w, kind=kind) for sym, name, w, kind in rows],
        )
