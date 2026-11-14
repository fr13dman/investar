"""Curated niche catalog: the source of truth for niche membership.

Edit this file and run `uv run investar load-niches` to apply it. Tickers use Yahoo format (BRK-B).
`stocks` and `etfs` can sit on a parent (broad theme ETFs) or on a sub-niche. Symbols outside the
S&P 500 and Nasdaq-100 are tracked automatically (prices, profile, metrics) once listed here.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NicheSpec:
    slug: str
    name: str
    description: str
    stocks: tuple[str, ...] = ()
    etfs: tuple[str, ...] = ()
    children: tuple["NicheSpec", ...] = field(default_factory=tuple)


CATALOG: tuple[NicheSpec, ...] = (
    NicheSpec(
        "ai", "AI", "Companies building, hosting and selling artificial intelligence.",
        etfs=("AIQ", "CHAT"),
        children=(
            NicheSpec("ai-chips", "AI Chips", "Accelerators, custom silicon and memory for AI training and inference.",
                      stocks=("NVDA", "AMD", "AVGO", "MRVL", "ARM", "TSM", "MU"), etfs=("SMH", "SOXX")),
            NicheSpec("hyperscalers", "Hyperscalers", "Public clouds running AI at global scale.",
                      stocks=("MSFT", "AMZN", "GOOGL", "META", "ORCL")),
            NicheSpec("neoclouds", "Neoclouds", "GPU-first clouds renting AI compute.",
                      stocks=("CRWV", "NBIS", "IREN", "APLD", "CIFR", "WULF")),
            NicheSpec("ai-networking-datacenter", "AI Networking and Data Center",
                      "Networking, servers, power and cooling for AI data centers.",
                      stocks=("ANET", "VRT", "SMCI", "DELL", "CLS", "EQIX", "DLR", "CRDO", "ALAB")),
            NicheSpec("ai-software", "AI Software", "Platforms and applications built on AI models.",
                      stocks=("PLTR", "NOW", "SNOW", "DDOG", "AI", "PATH")),
        ),
    ),
    NicheSpec(
        "energy-transition", "Energy Transition", "Low-carbon power generation and its fuel supply chain.",
        etfs=("URA", "NLR"),
        children=(
            NicheSpec("nuclear-operators", "Nuclear Operators", "Utilities and power producers running nuclear fleets.",
                      stocks=("CEG", "VST", "TLN")),
            NicheSpec("small-modular-reactors", "Small Modular Reactors", "Developers and suppliers of SMRs and microreactors.",
                      stocks=("OKLO", "SMR", "NNE", "BWXT", "GEV")),
            NicheSpec("uranium-fuel", "Uranium and Fuel", "Uranium miners, enrichment and fuel services.",
                      stocks=("CCJ", "LEU", "UEC", "UUUU", "NXE", "DNN"), etfs=("URNM",)),
        ),
    ),
    NicheSpec(
        "quantum-computing", "Quantum Computing", "Quantum hardware, software and the incumbents investing in it.",
        etfs=("QTUM",),
        children=(
            NicheSpec("quantum-pure-plays", "Quantum Pure Plays", "Companies whose main business is quantum computing.",
                      stocks=("IONQ", "RGTI", "QBTS", "QUBT")),
            NicheSpec("quantum-incumbents", "Quantum Incumbents", "Large companies with major quantum programs.",
                      stocks=("IBM", "GOOGL", "MSFT", "HON")),
        ),
    ),
    NicheSpec(
        "robotics", "Robotics", "Industrial automation, surgical robots and autonomous machines.",
        etfs=("BOTZ", "ROBO"),
        children=(
            NicheSpec("industrial-automation", "Industrial Automation", "Factory and warehouse robotics and controls.",
                      stocks=("ROK", "TER", "SYM", "CGNX")),
            NicheSpec("surgical-robotics", "Surgical Robotics", "Robot-assisted surgery systems.",
                      stocks=("ISRG", "PRCT")),
            NicheSpec("autonomy-humanoids", "Autonomy and Humanoids", "Self-driving, delivery robots and humanoids.",
                      stocks=("TSLA", "MBLY", "SERV")),
        ),
    ),
    NicheSpec(
        "cybersecurity", "Cybersecurity", "Security software and services.",
        etfs=("CIBR", "HACK", "BUG"),
        children=(
            NicheSpec("security-platforms", "Security Platforms", "Broad network, endpoint and cloud security suites.",
                      stocks=("PANW", "CRWD", "FTNT", "ZS", "CHKP")),
            NicheSpec("identity-cloud-security", "Identity and Cloud Security",
                      "Identity, zero-trust edge and data security.",
                      stocks=("OKTA", "NET", "S", "TENB", "RBRK")),
        ),
    ),
)
