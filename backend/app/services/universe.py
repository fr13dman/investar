"""SQL building blocks for "which symbols are tracked" and niche membership."""

from sqlalchemy import or_, select

from app.models import Company, Niche, NicheMember


def in_universe():
    """Index members plus curated and user-added extras (benchmarks are filtered separately)."""
    return Company.in_sp500 | Company.in_ndx100 | Company.extra_source.is_not(None)


def niche_member_tickers(slug: str):
    """Subquery of tickers in a niche, including its sub-niches."""
    target = select(Niche.id).where(Niche.slug == slug).scalar_subquery()
    ids = select(Niche.id).where(or_(Niche.id == target, Niche.parent_id == target))
    return select(NicheMember.ticker).where(NicheMember.niche_id.in_(ids))
