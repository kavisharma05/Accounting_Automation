import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.entities  # noqa: F401
from app.core.database import Base
from app.models.entities import Organization


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    org = Organization(name="Test Org")
    session.add(org)
    session.commit()
    yield session, org
    session.close()
