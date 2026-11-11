"""Map free-text jurisdictions ("Delaware, U.S.", "England and Wales", "PRC") to ISO 3166 countries."""

import re
from dataclasses import dataclass
from functools import lru_cache

import pycountry


@dataclass(frozen=True)
class Country:
    name: str
    alpha2: str
    numeric: str


US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware", "florida",
    "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york", "north carolina", "north dakota", "ohio", "oklahoma",
    "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota", "tennessee", "texas", "utah",
    "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming", "district of columbia",
}
US_MARKERS = re.compile(r"\b(u\.?s\.?a?\.?|united states( of america)?)(?=\W|$)", re.I)
ALIASES = {
    "england": "GB", "scotland": "GB", "wales": "GB", "northern ireland": "GB", "england and wales": "GB",
    "uk": "GB", "u.k.": "GB", "great britain": "GB", "britain": "GB",
    "korea": "KR", "south korea": "KR", "republic of korea": "KR",
    "prc": "CN", "p.r.c.": "CN", "people's republic of china": "CN", "peoples republic of china": "CN", "china (prc)": "CN",
    "turkey": "TR", "türkiye": "TR", "turkiye": "TR", "russia": "RU", "vietnam": "VN", "viet nam": "VN",
    "taiwan": "TW", "republic of china": "TW", "hong kong sar": "HK", "macau": "MO", "macao": "MO",
    "uae": "AE", "u.a.e.": "AE", "holland": "NL", "the netherlands": "NL", "czech republic": "CZ",
    "ivory coast": "CI", "republic of ireland": "IE", "brasil": "BR", "kingdom of saudi arabia": "SA",
    "british virgin islands": "VG", "bvi": "VG", "virgin islands (british)": "VG", "us virgin islands": "VI", "u.s. virgin islands": "VI",
    "luxemburg": "LU", "curacao": "CW", "curaçao": "CW", "bolivia": "BO", "venezuela": "VE", "iran": "IR",
    "laos": "LA", "moldova": "MD", "tanzania": "TZ", "syria": "SY", "the bahamas": "BS", "bahamas": "BS",
    "channel islands": "JE", "dubai": "AE", "abu dhabi": "AE", "puerto rico": "PR",
}


def _country(alpha2: str) -> Country:
    c = pycountry.countries.get(alpha_2=alpha2)
    return Country(getattr(c, "common_name", None) or c.name, c.alpha_2, c.numeric)


@lru_cache
def _name_index() -> list[tuple[str, str]]:
    names: dict[str, str] = {}
    for c in pycountry.countries:
        for attr in ("name", "common_name", "official_name"):
            v = getattr(c, attr, None)
            if v and len(v) > 3:
                names[v.lower()] = c.alpha_2
    names.update(ALIASES)
    return sorted(names.items(), key=lambda kv: -len(kv[0]))


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip(" .,;:*")
    return re.sub(r"^(the )?(state of|commonwealth of|province of|republic of the) ", "", text, flags=re.I)


def resolve_country(jurisdiction: str | None) -> Country | None:
    if not jurisdiction:
        return None
    text = _clean(jurisdiction)
    low = text.lower()
    if not low:
        return None
    if low in ALIASES:
        return _country(ALIASES[low])
    parts = [p.strip(" .") for p in re.split(r"[,/;()]| and ", low) if p.strip(" .")]
    if any(p in US_STATES for p in parts) or (US_MARKERS.search(low) and "virgin" not in low):
        return _country("US")
    for part in reversed(parts):
        if part in ALIASES:
            return _country(ALIASES[part])
        try:
            return _country(pycountry.countries.lookup(part).alpha_2)
        except LookupError:
            pass
    for name, alpha2 in _name_index():
        if re.search(rf"\b{re.escape(name)}\b", low):
            return _country(alpha2)
    return None


def country_from_xbrl_member(member: str) -> Country | None:
    """`country:US` style members from SEC's country taxonomy."""
    if member.lower().startswith("country:"):
        code = member.split(":", 1)[1].upper()
        if pycountry.countries.get(alpha_2=code):
            return _country(code)
    return None
