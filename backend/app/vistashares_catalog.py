"""VistaShares LLC fund metadata: families and tickers for the issuer ETF section."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VistaSharesFund:
    ticker: str
    name: str
    family: str  # target15 | supercycle | shield
    family_name: str


# Family display order and labels used by /etfs/vistashares.
FAMILIES: tuple[tuple[str, str], ...] = (
    ("target15", "Target 15"),
    ("supercycle", "Supercycle"),
    ("shield", "Shield"),
)

VISTASHARES_FUNDS: tuple[VistaSharesFund, ...] = (
    VistaSharesFund("OMAH", "VistaShares Target 15 Berkshire Select Income ETF", "target15", "Target 15"),
    VistaSharesFund("ACKY", "VistaShares Target 15 ACKtivist Distribution ETF", "target15", "Target 15"),
    VistaSharesFund("DRKY", "VistaShares Target 15 DRUKMacro Distribution ETF", "target15", "Target 15"),
    VistaSharesFund("TPRY", "VistaShares Target 15 TEPRTantrum Contrarian Distribution ETF", "target15", "Target 15"),
    VistaSharesFund("SIOO", "VistaShares Target 15 S&P 100 Distribution ETF", "target15", "Target 15"),
    VistaSharesFund("QUSA", "VistaShares Target 15 USA Quality Income ETF", "target15", "Target 15"),
    VistaSharesFund("AIS", "VistaShares Artificial Intelligence Supercycle ETF", "supercycle", "Supercycle"),
    VistaSharesFund("POW", "VistaShares Electrification Supercycle ETF", "supercycle", "Supercycle"),
    VistaSharesFund("GALX", "VistaShares Space Supercycle ETF", "supercycle", "Supercycle"),
    VistaSharesFund("RTOO", "VistaShares Robotics Supercycle ETF", "supercycle", "Supercycle"),
    VistaSharesFund("AMMO", "VistaShares Defense Supercycle ETF", "supercycle", "Supercycle"),
    VistaSharesFund("VOOB", "VistaShares Shield S&P 500 Enhanced Protection ETF", "shield", "Shield"),
    VistaSharesFund("QQQB", "VistaShares Shield NASDAQ 100 Enhanced Protection ETF", "shield", "Shield"),
)

VISTASHARES_TICKERS: frozenset[str] = frozenset(f.ticker for f in VISTASHARES_FUNDS)
VISTASHARES_BY_TICKER: dict[str, VistaSharesFund] = {f.ticker: f for f in VISTASHARES_FUNDS}


def is_vistashares(ticker: str) -> bool:
    return ticker.strip().upper() in VISTASHARES_TICKERS
