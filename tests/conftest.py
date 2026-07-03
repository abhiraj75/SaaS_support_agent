import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import DATABASE_URL
from app.database import get_db
from app.main import app
from app.models import Base
from app.seed import seed

engine = create_engine(DATABASE_URL)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    seed()


@pytest.fixture(autouse=True)
def _isolate_db():
    # Override get_db so the app's own writes join a per-test transaction that is
    # rolled back on teardown; savepoints let the app commit without persisting.
    connection = engine.connect()
    transaction = connection.begin()

    def override_get_db():
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield connection
    finally:
        app.dependency_overrides.pop(get_db, None)
        transaction.rollback()
        connection.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db(_isolate_db):
    session = Session(bind=_isolate_db, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
