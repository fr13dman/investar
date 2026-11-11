"""SEC EDGAR client: companyfacts, submissions, filing indexes and documents.
Fair-access rules: declared User-Agent with contact info and at most 10 requests/second."""

import re
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup

from app import http
from app.config import get_settings

DATA = "https://data.sec.gov"
ARCHIVES = "https://www.sec.gov/Archives/edgar/data"

REVENUE_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
]
EPS_CONCEPTS = ["EarningsPerShareDiluted", "EarningsPerShareBasic"]
NET_INCOME_CONCEPTS = ["NetIncomeLoss", "ProfitLoss"]


@dataclass
class Filing:
    accession: str
    form: str
    filing_date: date
    primary_document: str

    @property
    def folder(self) -> str:
        return self.accession.replace("-", "")


@dataclass
class IndexEntry:
    description: str
    document: str
    type: str


@dataclass
class AnnualFact:
    concept: str
    unit: str
    start: date | None
    end: date
    value: float
    form: str | None
    filed: date | None


def _get(url: str):
    http.LIMITERS["sec"].acquire()
    with http.client(get_settings().sec_user_agent, timeout=60) as c:
        r = c.get(url)
        r.raise_for_status()
        return r


def parse_filings(submissions: dict, forms: tuple[str, ...]) -> list[Filing]:
    recent = submissions.get("filings", {}).get("recent", {})
    out = []
    for i, form in enumerate(recent.get("form", [])):
        if form in forms:
            out.append(Filing(recent["accessionNumber"][i], form, date.fromisoformat(recent["filingDate"][i]),
                              recent["primaryDocument"][i]))
    return sorted(out, key=lambda f: f.filing_date, reverse=True)


def parse_filing_index(html: str) -> list[IndexEntry]:
    soup = BeautifulSoup(html, "lxml")
    entries = []
    for row in soup.select("table.tableFile tr") or soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        if len(cells) >= 4:
            doc = cells[2].replace("iXBRL", "").strip()
            entries.append(IndexEntry(description=cells[1], document=doc, type=cells[3]))
    return entries


def find_instance_document(entries: list[IndexEntry]) -> str | None:
    for e in entries:
        if "EXTRACTED XBRL INSTANCE" in e.description.upper() or e.type.upper() == "EX-101.INS":
            return e.document
    return None


def find_exhibit21(entries: list[IndexEntry]) -> str | None:
    for e in entries:
        if re.match(r"EX-21(\.\d+)?$", e.type.upper()) and e.document.lower().endswith((".htm", ".html", ".txt")):
            return e.document
    return None


def annual_facts(companyfacts: dict, concepts: list[str], unit: str) -> list[AnnualFact]:
    """Full-year (330-400 day) values from 10-K filings, de-duplicated by period end (latest filing wins).
    Uses the first concept in `concepts` that has data for each period end."""
    by_end: dict[date, AnnualFact] = {}
    gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    for concept in concepts:
        for f in gaap.get(concept, {}).get("units", {}).get(unit, []):
            if not str(f.get("form", "")).startswith("10-K") or not f.get("start"):
                continue
            start, end = date.fromisoformat(f["start"]), date.fromisoformat(f["end"])
            if not 330 <= (end - start).days <= 400:
                continue
            filed = date.fromisoformat(f["filed"]) if f.get("filed") else None
            current = by_end.get(end)
            if current is None or (current.concept == concept and (filed or date.min) > (current.filed or date.min)):
                by_end[end] = AnnualFact(concept, unit, start, end, float(f["val"]), f.get("form"), filed)
    return [by_end[k] for k in sorted(by_end)]


class SecEdgar:
    def company_facts(self, cik: str) -> dict:
        return _get(f"{DATA}/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json").json()

    def submissions(self, cik: str) -> dict:
        return _get(f"{DATA}/submissions/CIK{cik.zfill(10)}.json").json()

    def latest_filing(self, cik: str, forms: tuple[str, ...]) -> Filing | None:
        filings = parse_filings(self.submissions(cik), forms)
        return filings[0] if filings else None

    def filing_index(self, cik: str, filing: Filing) -> list[IndexEntry]:
        url = f"{ARCHIVES}/{int(cik)}/{filing.folder}/{filing.accession}-index.htm"
        return parse_filing_index(_get(url).text)

    def document(self, cik: str, filing: Filing, name: str) -> bytes:
        return _get(f"{ARCHIVES}/{int(cik)}/{filing.folder}/{name}").content
