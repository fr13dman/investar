"""CEO tenures from Wikidata: company (P5531 = SEC CIK) -> chief executive officer (P169) with
start time (P580) / end time (P582) qualifiers."""

from dataclasses import dataclass
from datetime import date

from app import http

ENDPOINT = "https://query.wikidata.org/sparql"
QUERY = """
SELECT ?ceoLabel ?start ?end WHERE {
  VALUES ?cik { "%(cik10)s" "%(cik)s" }
  ?company wdt:P5531 ?cik .
  ?company p:P169 ?st .
  ?st ps:P169 ?ceo .
  OPTIONAL { ?st pq:P580 ?start }
  OPTIONAL { ?st pq:P582 ?end }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


@dataclass
class Tenure:
    name: str
    start: date | None
    end: date | None


def _date(binding: dict | None) -> date | None:
    if not binding:
        return None
    try:
        return date.fromisoformat(binding["value"][:10])
    except ValueError:
        return None


def parse_tenures(payload: dict) -> list[Tenure]:
    out = [
        Tenure(b["ceoLabel"]["value"], _date(b.get("start")), _date(b.get("end")))
        for b in payload.get("results", {}).get("bindings", [])
        if b.get("ceoLabel")
    ]
    return sorted(out, key=lambda t: t.start or date.min)


class Wikidata:
    def ceo_tenures(self, cik: str) -> list[Tenure]:
        http.LIMITERS["wikidata"].acquire()
        q = QUERY % {"cik10": cik.zfill(10), "cik": str(int(cik))}
        with http.client() as c:
            r = c.get(ENDPOINT, params={"query": q}, headers={"Accept": "application/sparql-results+json"})
            r.raise_for_status()
            return parse_tenures(r.json())
