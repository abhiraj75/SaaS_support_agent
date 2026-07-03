import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL
from app.main import app
from app.models import Base
from app.seed import seed

engine = create_engine(DATABASE_URL)
TestSession = sessionmaker(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    seed()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    session = TestSession()
    yield session
    session.close()

