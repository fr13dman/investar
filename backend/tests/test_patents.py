import io
import zipfile
from datetime import date

import httpx
import pytest
import respx

from app.models import Company, PatentAssigneeMap
from app.providers import registry
from app.providers.base import PatentRecord
from app.providers.patents_bulk import Matcher
from app.providers.patents_patentsview import (
    Assignee,
    PatentsViewApi,
    PatentsViewUnavailable,
    assignee_clause,
    build_query,
    parse_patents,
    parse_publications,
)
from app.services import patents as svc

TODAY = date(2026, 11, 10)


def test_core_name_and_default_assignees():
    assert svc.core_name("Apple Inc.") == "Apple"
    assert svc.core_name("The Goldman Sachs Group, Inc.") == "The Goldman Sachs"
    assert svc.core_name("Exxon Mobil Corporation") == "Exxon Mobil"
    assert svc.default_assignees("ORCL", "Oracle Corporation") == [("Oracle Corporation", "exact"), ("Oracle ", "prefix")]
    assert ("Google LLC", "exact") in svc.default_assignees("GOOGL", "Alphabet Inc.")


def test_query_building():
    assert assignee_clause([Assignee("Apple Inc.")]) == {"assignees.assignee_organization": "Apple Inc."}
    q = build_query([Assignee("Apple Inc."), Assignee("Apple ", "prefix")], "patent_date", date(2017, 1, 1), date(2017, 12, 31))
    assert q == {"_and": [
        {"_or": [{"assignees.assignee_organization": "Apple Inc."}, {"_begins": {"assignees.assignee_organization": "Apple "}}]},
        {"_gte": {"patent_date": "2017-01-01"}},
        {"_lte": {"patent_date": "2017-12-31"}},
    ]}


def test_parse_api_payloads():
    granted = parse_patents({"patents": [{"patent_id": "12000001", "patent_title": "Foldable display", "patent_abstract": "A display.",
                                          "patent_date": "2026-10-01", "assignees": [{"assignee_organization": "Apple Inc."}],
                                          "cpc_current": [{"cpc_subclass_id": "G06F"}, {"cpc_subclass_id": "H04M"}]}]})
    assert granted[0] == PatentRecord("granted", "12000001", "Foldable display", "A display.", date(2026, 10, 1), "G06F", "Apple Inc.")
    apps = parse_publications({"publications": [{"document_number": "20260123456", "publication_title": "Wearable",
                                                 "publication_date": "2026-09-03", "cpc_current": []}]})
    assert apps[0].kind == "application" and apps[0].cpc_class is None


def test_api_requires_key(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "patentsview_api_key", "")
    with pytest.raises(PatentsViewUnavailable, match="import-patents-bulk"):
        PatentsViewApi().count("granted", [Assignee("Apple Inc.")], date(2026, 1, 1), date(2026, 12, 31))


@respx.mock
def test_api_unreachable_and_success(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "patentsview_api_key", "k")
    route = respx.post("https://search.patentsview.org/api/v1/patent/")
    route.side_effect = httpx.ConnectError("down")
    with pytest.raises(PatentsViewUnavailable, match="unreachable"):
        PatentsViewApi().count("granted", [Assignee("Apple Inc.")], date(2026, 1, 1), date(2026, 12, 31))

    route.side_effect = None
    route.return_value = httpx.Response(200, json={"error": False, "count": 1, "total_hits": 2345, "patents": [{"patent_id": "1"}]})
    assert PatentsViewApi().count("granted", [Assignee("Apple Inc.")], date(2026, 1, 1), date(2026, 12, 31)) == 2345
    assert route.calls.last.request.headers["X-Api-Key"] == "k"


class FakePatents:
    def count(self, kind, assignees, start, end):
        return 1000 + start.year % 100

    def search(self, kind, assignees, start, size):
        if kind == "granted":
            recs = [PatentRecord("granted", str(12_000_000 + i), f"Invention {i}", "Abstract", date(2026, 10, 1 + i % 28),
                                 "G06F" if i % 3 else "H04W", "Apple Inc.") for i in range(120)]
            return recs, 25_000
        recs = [PatentRecord("application", str(20_260_000_000 + i), f"Pending {i}", None, date(2026, 9, 1 + i % 28),
                             "G06N", "Apple Inc.") for i in range(30)]
        return recs, 4321


def test_refresh_patents_and_payload(seeded):
    registry.override(patents=FakePatents())
    svc.refresh_patents(seeded, "AAPL", today=TODAY)
    body = svc.patents_payload(seeded, "AAPL")
    g = body["granted"]
    assert [r["year"] for r in g["by_year"]] == [str(y) for y in range(2017, 2027)]
    assert g["total_10y"] == sum(1000 + y % 100 for y in range(2017, 2027))
    assert len(g["recent"]) == svc.RECENT_GRANTED
    assert g["top_cpc"]["items"][0] == {"code": "G06F", "title": "Electric digital data processing", "count": 80}
    assert g["recent"][0]["url"].startswith("https://patents.google.com/patent/US")
    a = body["applications"]
    assert a["total_24m"] == 4321 and len(a["recent"]) == 30
    assert a["recent"][0]["url"].endswith("A1")
    assert body["assignees"] == [{"assignee_name": "Apple Inc.", "match": "exact", "source": "curated"}]
    assert body["source"] == "patentsview_api"


def test_assignee_map_editing(seeded):
    svc.ensure_assignee_map(seeded, "ORCL")
    rows = svc.set_assignees(seeded, "ORCL", [{"assignee_name": "Oracle International Corporation", "match": "exact"},
                                              {"assignee_name": "Oracle", "match": "prefix"},
                                              {"assignee_name": "  ", "match": "exact"}])
    assert sorted((r.assignee_name, r.match, r.source) for r in rows) == [
        ("Oracle ", "prefix", "manual"), ("Oracle International Corporation", "exact", "manual")]


def test_matcher_prefix_does_not_overmatch():
    m = Matcher.from_map([("AAPL", "Apple ", "prefix"), ("AAPL", "Apple Inc.", "exact"), ("AMAT", "Applied Materials, Inc.", "exact")])
    assert m.tickers("APPLE INC.") == {"AAPL"}
    assert m.tickers("Apple Computer, Inc.") == {"AAPL"}
    assert m.tickers("Applied Materials, Inc.") == {"AMAT"}
    assert m.tickers("Applebee's") == set()


def _write_tsv(path, header, rows, zipped=False):
    content = "\t".join(header) + "\n" + "\n".join("\t".join(r) for r in rows) + "\n"
    if zipped:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr(path.name.removesuffix(".zip"), content)
        path.write_bytes(buf.getvalue())
    else:
        path.write_text(content)


def test_bulk_import(seeded, tmp_path):
    _write_tsv(tmp_path / "g_patent.tsv.zip", ["patent_id", "patent_type", "patent_date", "patent_title", "wipo_kind"], [
        ["11000001", "utility", "2018-05-01", "Touch screen", "B2"],
        ["11000002", "utility", "2026-03-01", "Neural engine", "B2"],
        ["10000003", "utility", "2012-01-01", "Too old", "B2"],
        ["11000004", "utility", "2025-06-01", "Not Apple", "B2"],
    ], zipped=True)
    _write_tsv(tmp_path / "g_assignee_disambiguated.tsv", ["patent_id", "assignee_sequence", "assignee_id",
                                                            "disambig_assignee_organization"], [
        ["11000001", "0", "a1", "Apple Inc."], ["11000002", "0", "a1", "Apple Inc."], ["10000003", "0", "a1", "Apple Inc."],
        ["11000004", "0", "a2", "Applied Materials, Inc."],
    ])
    _write_tsv(tmp_path / "g_cpc_current.tsv", ["patent_id", "cpc_sequence", "cpc_section", "cpc_subclass"], [
        ["11000001", "1", "G", "G06T"], ["11000001", "0", "G", "G06F"], ["11000002", "0", "G", "G06N"],
    ])
    _write_tsv(tmp_path / "g_patent_abstract.tsv", ["patent_id", "patent_abstract"], [["11000002", "An accelerator."]])
    _write_tsv(tmp_path / "pg_published_application.tsv", ["pgpub_id", "published_date", "application_title"], [
        ["20260100001", "2026-02-05", "Smart ring"], ["20230100002", "2023-02-05", "Old pub"],
    ])
    _write_tsv(tmp_path / "pg_assignee_disambiguated.tsv", ["pgpub_id", "assignee_sequence", "disambig_assignee_organization"], [
        ["20260100001", "0", "Apple Inc."], ["20230100002", "0", "Apple Inc."],
    ])

    imported = svc.import_bulk(seeded, tmp_path, tickers=["AAPL"], today=TODAY)
    assert imported == {"AAPL": 3}
    body = svc.patents_payload(seeded, "AAPL")
    assert body["source"] == "patentsview_bulk"
    years = {r["year"]: r["count"] for r in body["granted"]["by_year"]}
    assert years["2018"] == 1 and years["2026"] == 1 and sum(years.values()) == 2
    recent = {p["number"]: p for p in body["granted"]["recent"]}
    assert recent["11000001"]["cpc_class"] == "G06F"  # lowest cpc_sequence wins
    assert recent["11000002"]["abstract"] == "An accelerator."
    assert body["applications"]["total_24m"] == 1
    assert body["applications"]["recent"][0]["title"] == "Smart ring"


def test_patents_endpoints(client, seeded):
    registry.override(patents=FakePatents())
    first = client.get("/api/companies/AAPL/patents").json()
    assert first["refresh"]["refreshing"] is True
    assert first["assignees"][0]["assignee_name"] == "Apple Inc."
    second = client.get("/api/companies/AAPL/patents").json()
    assert second["granted"]["total_10y"] > 0 and second["applications"]["total_24m"] == 4321

    body = client.put("/api/companies/AAPL/patent-assignees",
                      json=[{"assignee_name": "Apple Inc.", "match": "exact"}, {"assignee_name": "Beats Electronics", "match": "prefix"}]).json()
    assert {a["assignee_name"] for a in body["assignees"]} == {"Apple Inc.", "Beats Electronics"}
    assert seeded.query(PatentAssigneeMap).filter_by(ticker="AAPL").count() == 2


def test_patents_api_down_reports_error(client, seeded):
    class Down:
        def count(self, *a):
            raise PatentsViewUnavailable("PatentsView API unreachable (ConnectError); use `investar import-patents-bulk` instead")

    registry.override(patents=Down())
    client.get("/api/companies/MSFT/patents")
    body = client.get("/api/companies/MSFT/patents").json()
    assert body["refresh"]["status"] == "error" and "import-patents-bulk" in body["refresh"]["message"]
    assert body["granted"]["total_10y"] is None
    assert seeded.get(Company, "MSFT") is not None
