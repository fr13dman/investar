from sqlalchemy import create_engine, inspect, text

from app.db import Base
from app.migrate import upgrade_head


def test_alembic_head_matches_models(tmp_path):
    import app.models  # noqa: F401

    url = f"sqlite:///{tmp_path / 'mig.db'}"
    upgrade_head(url)
    insp = inspect(create_engine(url))
    tables = set(insp.get_table_names())
    assert set(Base.metadata.tables) <= tables
    for name, table in Base.metadata.tables.items():
        assert {c.name for c in table.columns} <= {c["name"] for c in insp.get_columns(name)}, name


def test_upgrade_preserves_existing_geo_rows(tmp_path):
    from alembic import command
    from alembic.config import Config

    from app.config import BACKEND_DIR

    url = f"sqlite:///{tmp_path / 'old.db'}"
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "8537b4ea2b30")
    eng = create_engine(url)
    with eng.begin() as c:
        c.execute(text("INSERT INTO companies (ticker, name, in_sp500, in_ndx100, is_benchmark) VALUES ('AAPL','Apple',1,1,0)"))
        c.execute(text("INSERT INTO geo_revenue (ticker, period_end, region, member, revenue) "
                       "VALUES ('AAPL','2026-09-26','United States','country:US',1.0)"))
    command.upgrade(cfg, "head")
    with eng.connect() as c:
        assert c.execute(text("SELECT axis FROM geo_revenue")).scalar() == "geographic"


def test_niches_migration_defaults_existing_companies_to_index_stocks(tmp_path):
    from alembic import command
    from alembic.config import Config

    from app.config import BACKEND_DIR

    url = f"sqlite:///{tmp_path / 'pre_niches.db'}"
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "55980ed370b4")
    eng = create_engine(url)
    with eng.begin() as c:
        c.execute(text("INSERT INTO companies (ticker, name, in_sp500, in_ndx100, is_benchmark) VALUES ('AAPL','Apple',1,1,0)"))
    command.upgrade(cfg, "head")
    with eng.connect() as c:
        assert c.execute(text("SELECT asset_type, extra_source FROM companies")).one() == ("stock", None)
    command.downgrade(cfg, "55980ed370b4")
    assert "niches" not in inspect(create_engine(url)).get_table_names()
