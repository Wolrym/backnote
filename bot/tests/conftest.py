from pathlib import Path

import pytest

from backnote.db import create_engine, create_sessionmaker
from backnote.db.migrate import upgrade
from backnote.services import Services

ADMIN_ID = 1000


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    # Tests run against the real migrations, not create_all.
    upgrade(url)
    return url


@pytest.fixture
async def engine(db_url: str):
    engine = create_engine(db_url)
    yield engine
    await engine.dispose()


@pytest.fixture
def svc(engine) -> Services:
    return Services.create(create_sessionmaker(engine), ADMIN_ID)
