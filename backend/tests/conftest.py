import pytest
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal, engine
from backend.app.db.models.models_v1 import Base


@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Session DB isolée par test.
    Utilise la vraie DB (comme l'app),
    rollback automatique après chaque test.
    """

    # S'assure que le schéma existe
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
