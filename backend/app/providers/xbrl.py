"""Minimal XBRL instance parser (the "EXTRACTED XBRL INSTANCE DOCUMENT" SEC builds for inline filings).

SEC's companyfacts API only returns entity-wide facts; dimensional facts (revenue by geography) and the
executive-compensation (ecd) taxonomy are only available from the filing's own instance document."""

from dataclasses import dataclass, field
from datetime import date

from lxml import etree

XBRLI = "http://www.xbrl.org/2003/instance"
XBRLDI = "http://xbrl.org/2006/xbrldi"


@dataclass
class Context:
    id: str
    start: date | None
    end: date | None
    dims: dict[str, str] = field(default_factory=dict)

    @property
    def duration_days(self) -> int | None:
        return (self.end - self.start).days if self.start and self.end else None


@dataclass
class Fact:
    prefix: str
    name: str
    value: str
    context: Context
    unit: str | None


def _d(text: str | None) -> date | None:
    return date.fromisoformat(text.strip()[:10]) if text else None


def parse_instance(content: bytes) -> list[Fact]:
    root = etree.fromstring(content, parser=etree.XMLParser(huge_tree=True, recover=True))
    ns_prefix = {uri: p for p, uri in (root.nsmap or {}).items() if p}
    contexts: dict[str, Context] = {}
    for c in root.iter(f"{{{XBRLI}}}context"):
        end = c.findtext(f".//{{{XBRLI}}}endDate") or c.findtext(f".//{{{XBRLI}}}instant")
        dims = {m.get("dimension"): (m.text or "").strip() for m in c.iter(f"{{{XBRLDI}}}explicitMember")}
        contexts[c.get("id")] = Context(c.get("id"), _d(c.findtext(f".//{{{XBRLI}}}startDate")), _d(end), dims)
    facts = []
    for el in root:
        if not isinstance(el.tag, str):
            continue
        ctx_ref = el.get("contextRef")
        if not ctx_ref or ctx_ref not in contexts:
            continue
        q = etree.QName(el)
        facts.append(
            Fact(
                prefix=ns_prefix.get(q.namespace, ""),
                name=q.localname,
                value=(el.text or "").strip(),
                context=contexts[ctx_ref],
                unit=el.get("unitRef"),
            )
        )
    return facts


def to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
