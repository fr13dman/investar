"""USPTO PatentsView PatentSearch API (https://search.patentsview.org/api/v1/).

Requires an API key (X-Api-Key header, 45 requests/minute). The API is moving to the USPTO Open Data Portal and
may be unavailable; `patents_bulk.py` imports the bulk TSV files as a fallback."""

from dataclasses import dataclass
from datetime import date

import httpx

from app import http
from app.config import get_settings
from app.providers.base import PatentRecord, ProviderUnavailable

BASE = "https://search.patentsview.org/api/v1"
PATENT_FIELDS = ["patent_id", "patent_title", "patent_abstract", "patent_date",
                 "assignees.assignee_organization", "cpc_current.cpc_subclass_id"]
PUBLICATION_FIELDS = ["document_number", "publication_title", "publication_abstract", "publication_date",
                      "assignees.assignee_organization", "cpc_current.cpc_subclass_id"]


class PatentsViewUnavailable(ProviderUnavailable):
    pass


@dataclass
class Assignee:
    name: str
    match: str = "exact"  # exact | prefix


def assignee_clause(assignees: list[Assignee]) -> dict:
    field = "assignees.assignee_organization"
    clauses = [{"_begins": {field: a.name}} if a.match == "prefix" else {field: a.name} for a in assignees]
    return clauses[0] if len(clauses) == 1 else {"_or": clauses}


def build_query(assignees: list[Assignee], date_field: str, start: date, end: date | None = None) -> dict:
    conds = [assignee_clause(assignees), {"_gte": {date_field: start.isoformat()}}]
    if end:
        conds.append({"_lte": {date_field: end.isoformat()}})
    return {"_and": conds}


def _first_cpc(item: dict) -> str | None:
    for c in item.get("cpc_current") or []:
        if c.get("cpc_subclass_id"):
            return c["cpc_subclass_id"]
    return None


def _first_assignee(item: dict) -> str | None:
    for a in item.get("assignees") or []:
        if a.get("assignee_organization"):
            return a["assignee_organization"]
    return None


def parse_patents(payload: dict) -> list[PatentRecord]:
    return [
        PatentRecord("granted", str(p["patent_id"]), p.get("patent_title"), p.get("patent_abstract"),
                     date.fromisoformat(p["patent_date"]) if p.get("patent_date") else None, _first_cpc(p), _first_assignee(p))
        for p in payload.get("patents") or []
    ]


def parse_publications(payload: dict) -> list[PatentRecord]:
    return [
        PatentRecord("application", str(p["document_number"]), p.get("publication_title"), p.get("publication_abstract"),
                     date.fromisoformat(p["publication_date"]) if p.get("publication_date") else None, _first_cpc(p),
                     _first_assignee(p))
        for p in payload.get("publications") or []
    ]


class PatentsViewApi:
    def _post(self, endpoint: str, body: dict) -> dict:
        key = get_settings().patentsview_api_key
        if not key:
            raise PatentsViewUnavailable("PATENTSVIEW_API_KEY is not set; use `investar import-patents-bulk` instead")
        http.LIMITERS["patentsview"].acquire()
        try:
            with http.client(timeout=60) as c:
                r = c.post(f"{BASE}/{endpoint}/", json=body, headers={"X-Api-Key": key})
        except httpx.TransportError as exc:
            raise PatentsViewUnavailable(f"PatentsView API unreachable ({exc.__class__.__name__}); "
                                         "use `investar import-patents-bulk` instead") from exc
        if r.status_code in (401, 403):
            raise PatentsViewUnavailable("PatentsView rejected the API key")
        r.raise_for_status()
        return r.json()

    def count(self, kind: str, assignees: list[Assignee], start: date, end: date) -> int:
        endpoint, field, id_field = (("patent", "patent_date", "patent_id") if kind == "granted"
                                     else ("publication", "publication_date", "document_number"))
        body = {"q": build_query(assignees, field, start, end), "f": [id_field], "o": {"size": 1}}
        return int(self._post(endpoint, body).get("total_hits", 0))

    def search(self, kind: str, assignees: list[Assignee], start: date, size: int) -> tuple[list[PatentRecord], int]:
        if kind == "granted":
            body = {"q": build_query(assignees, "patent_date", start), "f": PATENT_FIELDS,
                    "s": [{"patent_date": "desc"}], "o": {"size": size}}
            payload = self._post("patent", body)
            return parse_patents(payload), int(payload.get("total_hits", 0))
        body = {"q": build_query(assignees, "publication_date", start), "f": PUBLICATION_FIELDS,
                "s": [{"publication_date": "desc"}], "o": {"size": size}}
        payload = self._post("publication", body)
        return parse_publications(payload), int(payload.get("total_hits", 0))
