"""Offline fallback: import PatentsView bulk TSV files (USPTO Open Data Portal, data.uspto.gov/bulkdata).

Expected files (plain .tsv or zipped .tsv.zip) in one directory:
  granted:      g_patent, g_assignee_disambiguated, g_cpc_current (optional), g_patent_abstract (optional)
  pre-grant:    pg_published_application, pg_assignee_disambiguated, pg_cpc_current (optional)
The files are several GB; they are streamed in chunks and filtered to the companies in patent_assignee_map."""

import logging
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from app.providers.base import PatentRecord

log = logging.getLogger(__name__)
CHUNK = 500_000

ID_COLS = ("patent_id", "pgpub_id", "document_number")
ORG_COLS = ("disambig_assignee_organization", "assignee_organization")
DATE_COLS = ("patent_date", "published_date", "publication_date")
TITLE_COLS = ("patent_title", "application_title", "publication_title")
ABSTRACT_COLS = ("patent_abstract", "application_abstract", "publication_abstract")
CPC_COLS = ("cpc_subclass", "cpc_subclass_id")


@dataclass
class Matcher:
    exact: dict[str, set[str]]  # lowercased org -> tickers
    prefixes: list[tuple[str, str]]  # (lowercased prefix, ticker)

    @classmethod
    def from_map(cls, rows: list[tuple[str, str, str]]) -> "Matcher":
        exact: dict[str, set[str]] = defaultdict(set)
        prefixes = []
        for ticker, name, match in rows:
            if match == "prefix":
                prefixes.append((name.lower(), ticker))
            else:
                exact[name.strip().lower()].add(ticker)
        return cls(dict(exact), prefixes)

    def tickers(self, org: str) -> set[str]:
        low = org.strip().lower()
        out = set(self.exact.get(low, ()))
        out.update(t for p, t in self.prefixes if low.startswith(p) or low == p.strip())
        return out


def find_file(directory: Path, stem: str) -> Path | None:
    for suffix in (".tsv", ".tsv.zip", ".zip"):
        p = directory / f"{stem}{suffix}"
        if p.exists():
            return p
    return None


def _pick(columns, options) -> str | None:
    return next((c for c in options if c in columns), None)


def _chunks(path: Path) -> Iterator[pd.DataFrame]:
    yield from pd.read_csv(path, sep="\t", dtype=str, chunksize=CHUNK, keep_default_na=False, on_bad_lines="skip")


def match_assignees(path: Path, matcher: Matcher) -> dict[str, set[str]]:
    """document id -> tickers whose assignee names match."""
    hits: dict[str, set[str]] = defaultdict(set)
    for df in _chunks(path):
        id_col, org_col = _pick(df.columns, ID_COLS), _pick(df.columns, ORG_COLS)
        for doc_id, org in zip(df[id_col], df[org_col]):
            if org:
                t = matcher.tickers(org)
                if t:
                    hits[doc_id] |= t
    return hits


def first_cpc(path: Path | None, ids: set[str]) -> dict[str, str]:
    out: dict[str, tuple[int, str]] = {}
    if not path:
        return {}
    for df in _chunks(path):
        id_col, cpc_col = _pick(df.columns, ID_COLS), _pick(df.columns, CPC_COLS)
        seq = df["cpc_sequence"] if "cpc_sequence" in df.columns else pd.Series(["0"] * len(df))
        for doc_id, code, s in zip(df[id_col], df[cpc_col], seq):
            if doc_id in ids and code:
                rank = int(s) if str(s).isdigit() else 99
                if doc_id not in out or rank < out[doc_id][0]:
                    out[doc_id] = (rank, code)
    return {k: v[1] for k, v in out.items()}


def abstracts(path: Path | None, ids: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path:
        return out
    for df in _chunks(path):
        id_col, abs_col = _pick(df.columns, ID_COLS), _pick(df.columns, ABSTRACT_COLS)
        for doc_id, text in zip(df[id_col], df[abs_col]):
            if doc_id in ids:
                out[doc_id] = text
    return out


def load_documents(path: Path, hits: dict[str, set[str]], kind: str, since: date,
                   cpc: dict[str, str], extra_abstracts: dict[str, str]) -> dict[str, list[PatentRecord]]:
    by_ticker: dict[str, list[PatentRecord]] = defaultdict(list)
    for df in _chunks(path):
        cols = df.columns
        id_col, date_col = _pick(cols, ID_COLS), _pick(cols, DATE_COLS)
        title_col, abs_col = _pick(cols, TITLE_COLS), _pick(cols, ABSTRACT_COLS)
        sub = df[df[id_col].isin(hits.keys())]
        for _, row in sub.iterrows():
            try:
                d = date.fromisoformat(row[date_col][:10])
            except (TypeError, ValueError):
                continue
            if d < since:
                continue
            doc_id = row[id_col]
            rec = PatentRecord(kind, doc_id, row[title_col] if title_col else None,
                               (row[abs_col] if abs_col else None) or extra_abstracts.get(doc_id),
                               d, cpc.get(doc_id), None)
            for t in hits[doc_id]:
                by_ticker[t].append(rec)
    return by_ticker


def import_directory(directory: Path, assignee_rows: list[tuple[str, str, str]], granted_since: date,
                     applications_since: date) -> dict[str, dict[str, list[PatentRecord]]]:
    """Returns {"granted": {ticker: [...]}, "application": {ticker: [...]}} for whichever file sets are present."""
    matcher = Matcher.from_map(assignee_rows)
    result: dict[str, dict[str, list[PatentRecord]]] = {}
    sets = {
        "granted": ("g_patent", "g_assignee_disambiguated", "g_cpc_current", "g_patent_abstract", granted_since),
        "application": ("pg_published_application", "pg_assignee_disambiguated", "pg_cpc_current", None, applications_since),
    }
    for kind, (docs, assignees, cpc_file, abstract_file, since) in sets.items():
        docs_path, assignee_path = find_file(directory, docs), find_file(directory, assignees)
        if not docs_path or not assignee_path:
            log.info("skipping %s: %s or %s not found in %s", kind, docs, assignees, directory)
            continue
        hits = match_assignees(assignee_path, matcher)
        ids = set(hits)
        cpc = first_cpc(find_file(directory, cpc_file), ids)
        extra = abstracts(find_file(directory, abstract_file), ids) if abstract_file else {}
        result[kind] = load_documents(docs_path, hits, kind, since, cpc, extra)
    return result
