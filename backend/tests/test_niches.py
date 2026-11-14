from sqlalchemy import func, select

from app.models import Company, Niche, NicheMember
from app.niches_catalog import CATALOG, NicheSpec
from app.providers import registry
from app.seed import DEMO_CATALOG, seed_niches
from app.services.ingest import fill_ciks, universe_tickers
from app.services.niches import company_niches, load_catalog, niche_tree, set_user_niches
from app.services.research_jobs import research_tickers
from tests.conftest import SEED_END
from tests.fakes import FakeConstituents


def _seed(session):
    from app.seed import seed_market

    seed_market(session, end=SEED_END)
    seed_niches(session, end=SEED_END)


def _counts(session):
    return (session.scalar(select(func.count()).select_from(Niche)),
            session.scalar(select(func.count()).select_from(NicheMember)))


def test_load_catalog_is_idempotent(session):
    _seed(session)
    first = _counts(session)
    assert first == (6, 9)
    result = load_catalog(session, DEMO_CATALOG)
    assert _counts(session) == first
    assert result["new_tickers"] == []


def test_tree_parent_counts_are_union_of_children(session):
    _seed(session)
    tree = {n["slug"]: n for n in niche_tree(session)}
    assert list(tree) == ["ai", "energy-transition"]
    assert tree["ai"]["count"] == 7
    assert [c["slug"] for c in tree["ai"]["children"]] == ["ai-chips", "hyperscalers", "neoclouds"]
    assert {c["slug"]: c["count"] for c in tree["ai"]["children"]}["neoclouds"] == 1
    assert tree["energy-transition"]["count"] == 2  # URA on the parent + OKLO in a child


def test_catalog_marks_extras_and_etfs(session):
    _seed(session)
    crwv, ura, nvda = (session.get(Company, t) for t in ("CRWV", "URA", "NVDA"))
    assert crwv.extra_source == "curated" and not crwv.in_sp500
    assert ura.asset_type == "etf"
    assert nvda.extra_source == "curated" and nvda.in_sp500
    assert {"CRWV", "OKLO", "URA"} <= set(universe_tickers(session))


def test_user_tags_survive_reload_and_removed_curated_symbols_leave_universe(session):
    _seed(session)
    session.add(Company(ticker="NBIS", name="Nebius", extra_source="user"))
    session.commit()
    neo = session.scalar(select(Niche).where(Niche.slug == "neoclouds"))
    set_user_niches(session, "NBIS", [neo.id])

    smaller = (NicheSpec("ai", "AI", "AI", children=(NicheSpec("neoclouds", "Neoclouds", "GPU clouds"),)),)
    load_catalog(session, smaller)
    session.expire_all()
    assert session.scalar(select(func.count()).select_from(Niche)) == 2
    assert [n["slug"] for n in company_niches(session, "NBIS")] == ["neoclouds"]
    assert session.get(Company, "CRWV").extra_source is None
    assert "CRWV" not in universe_tickers(session)
    assert session.get(Company, "NBIS").extra_source == "user"


def test_set_user_niches_keeps_curated_tags(session):
    _seed(session)
    ids = {n.slug: n.id for n in session.scalars(select(Niche))}
    tags = set_user_niches(session, "CRWV", [ids["ai-chips"]])
    assert {(t["slug"], t["source"]) for t in tags} == {("neoclouds", "curated"), ("ai-chips", "user")}
    tags = set_user_niches(session, "CRWV", [])
    assert [(t["slug"], t["source"]) for t in tags] == [("neoclouds", "curated")]


def test_set_user_niches_rejects_unknown_ids(session):
    _seed(session)
    import pytest

    with pytest.raises(ValueError):
        set_user_niches(session, "CRWV", [9999])


def test_real_catalog_shape():
    slugs = [n.slug for p in CATALOG for n in (p, *p.children)]
    assert len(slugs) == len(set(slugs))
    assert {"ai", "hyperscalers", "neoclouds", "energy-transition", "nuclear-operators", "small-modular-reactors",
            "quantum-computing", "robotics", "cybersecurity"} <= set(slugs)
    assert all(p.children for p in CATALOG)
    stocks = {t for p in CATALOG for n in (p, *p.children) for t in n.stocks}
    etfs = {t for p in CATALOG for n in (p, *p.children) for t in n.etfs}
    assert not stocks & etfs


def test_real_catalog_loads_into_empty_db(session):
    result = load_catalog(session)
    assert {"CRWV", "NBIS", "OKLO", "CCJ", "URA"} <= set(result["new_tickers"])
    assert session.get(Company, "URA").asset_type == "etf"
    tree = {n["slug"]: n for n in niche_tree(session)}
    assert len(tree) == 5 and tree["ai"]["count"] > 20


def test_research_skips_etfs_and_non_sec(session):
    _seed(session)
    session.get(Company, "NVDA").cik = "0001045810"
    session.commit()
    registry.override(constituents=FakeConstituents())
    assert fill_ciks(session) == 1  # CRWV is in the fake SEC map; OKLO is not; URA is an ETF
    tickers = research_tickers(session)
    assert "CRWV" in tickers and "NVDA" in tickers
    assert "URA" not in tickers and "OKLO" not in tickers
