"""Niche catalog loading, the niche tree, and per-company niche tags."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Company, Niche, NicheMember
from app.niches_catalog import CATALOG, NicheSpec
from app.services.universe import in_universe


def _flatten(catalog: tuple[NicheSpec, ...]):
    for i, parent in enumerate(catalog):
        yield parent, None, i
        for j, child in enumerate(parent.children):
            yield child, parent.slug, j


def load_catalog(session: Session, catalog: tuple[NicheSpec, ...] = CATALOG) -> dict:
    """Idempotently apply the curated catalog. User tags survive; returns tickers that are new to the DB."""
    by_slug = {n.slug: n for n in session.scalars(select(Niche))}
    wanted: dict[str, NicheSpec] = {}
    for spec, parent_slug, order in _flatten(catalog):
        node = by_slug.get(spec.slug) or Niche(slug=spec.slug)
        node.name, node.description, node.sort_order = spec.name, spec.description, order
        node.parent_id = by_slug[parent_slug].id if parent_slug else None
        session.add(node)
        session.flush()
        by_slug[spec.slug] = node
        wanted[spec.slug] = spec
    session.execute(delete(Niche).where(Niche.slug.not_in(list(wanted))))
    session.flush()

    asset_types: dict[str, str] = {}
    desired: set[tuple[int, str]] = set()
    for slug, spec in wanted.items():
        for t in spec.stocks:
            asset_types.setdefault(t, "stock")
            desired.add((by_slug[slug].id, t))
        for t in spec.etfs:
            asset_types[t] = "etf"
            desired.add((by_slug[slug].id, t))

    companies = {c.ticker: c for c in session.scalars(select(Company))}
    new_tickers = []
    for t, kind in asset_types.items():
        comp = companies.get(t)
        if comp is None:
            comp = companies[t] = Company(ticker=t, name=t)
            new_tickers.append(t)
        comp.extra_source = "curated"
        comp.asset_type = kind
        session.add(comp)
    session.flush()

    members = {(m.niche_id, m.ticker): m for m in session.scalars(select(NicheMember))}
    for key, m in members.items():
        if m.source == "curated" and key not in desired:
            session.delete(m)
    for niche_id, t in desired:
        m = members.get((niche_id, t))
        if m is None:
            session.add(NicheMember(niche_id=niche_id, ticker=t, source="curated"))
        else:
            m.source = "curated"
    session.flush()

    user_tagged = set(session.scalars(select(NicheMember.ticker).where(NicheMember.source == "user")))
    for t, comp in companies.items():
        if comp.extra_source == "curated" and t not in asset_types:
            comp.extra_source = "user" if t in user_tagged else None
    session.commit()
    return {"niches": len(wanted), "members": len(desired), "new_tickers": sorted(new_tickers)}


def niche_tree(session: Session) -> list[dict]:
    niches = session.scalars(select(Niche).order_by(Niche.sort_order, Niche.name)).all()
    rows = session.execute(
        select(NicheMember.niche_id, NicheMember.ticker)
        .join(Company, Company.ticker == NicheMember.ticker)
        .where(~Company.is_benchmark, in_universe())
    ).all()
    tickers: dict[int, set[str]] = {}
    for niche_id, t in rows:
        tickers.setdefault(niche_id, set()).add(t)

    def node(n: Niche) -> dict:
        return {"id": n.id, "slug": n.slug, "name": n.name, "description": n.description,
                "count": len(tickers.get(n.id, set()))}

    tree = []
    for parent in (n for n in niches if n.parent_id is None):
        children = [n for n in niches if n.parent_id == parent.id]
        union = set(tickers.get(parent.id, set())).union(*(tickers.get(c.id, set()) for c in children))
        tree.append({**node(parent), "count": len(union), "children": [node(c) for c in children]})
    return tree


def company_niches(session: Session, ticker: str) -> list[dict]:
    parent = Niche.__table__.alias("parent")
    rows = session.execute(
        select(Niche, NicheMember.source, parent.c.slug, parent.c.name)
        .join(NicheMember, NicheMember.niche_id == Niche.id)
        .outerjoin(parent, parent.c.id == Niche.parent_id)
        .where(NicheMember.ticker == ticker)
        .order_by(Niche.sort_order, Niche.name)
    ).all()
    return [{"id": n.id, "slug": n.slug, "name": n.name, "parent_slug": ps, "parent_name": pn, "source": src}
            for n, src, ps, pn in rows]


def set_user_niches(session: Session, ticker: str, niche_ids: list[int]) -> list[dict]:
    """Replace a company's user-sourced tags; curated tags are left untouched."""
    wanted = set(niche_ids)
    known = set(session.scalars(select(Niche.id).where(Niche.id.in_(wanted)))) if wanted else set()
    if unknown := wanted - known:
        raise ValueError(f"unknown niche ids: {sorted(unknown)}")
    session.execute(delete(NicheMember).where(NicheMember.ticker == ticker, NicheMember.source == "user",
                                              NicheMember.niche_id.not_in(wanted)))
    have = set(session.scalars(select(NicheMember.niche_id).where(NicheMember.ticker == ticker)))
    for nid in wanted - have:
        session.add(NicheMember(niche_id=nid, ticker=ticker, source="user"))
    session.commit()
    return company_niches(session, ticker)
