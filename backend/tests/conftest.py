import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal, engine
from backend.app.db.models.models_v1 import Base


@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Session DB isolée par test.

    Utilise une transaction englobante + SAVEPOINT.
    TOUT est rollback à la fin du test, même après commit().
    """

    # S'assure que le schéma existe
    Base.metadata.create_all(bind=engine)

    connection = engine.connect()
    transaction = connection.begin()

    session = SessionLocal(bind=connection)

    # --- SAVEPOINT pattern ---
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
