import os
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("ENABLE_SCHEDULER", "false")
os.environ.setdefault("FINNHUB_API_KEY", "")
os.environ.setdefault("PATENTSVIEW_API_KEY", "")
os.environ.setdefault("SENTIMENT_MODEL", "vader")  # keep tests fast even when the FinBERT extra is installed
os.environ.setdefault("SENTIMENT_MODEL", "vader")  # keep tests fast even when the FinBERT extra is installed

from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.db import Base  # noqa: E402
from app.providers import registry  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
SEED_END = date(2026, 11, 10)  # a Tuesday


@pytest.fixture
def db_url(tmp_path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def session(db_url):
    import app.models  # noqa: F401

    db.configure(db_url)
    Base.metadata.create_all(db.engine)
    s = db.SessionLocal()
    yield s
    s.close()
    db.engine.dispose()
    registry.reset()


@pytest.fixture
def client(session):
    from app.main import create_app

    with TestClient(create_app(use_lifespan=False)) as c:
        yield c


@pytest.fixture
def seeded(session):
    from app.seed import seed_market

    seed_market(session, end=SEED_END)
    return session


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()
