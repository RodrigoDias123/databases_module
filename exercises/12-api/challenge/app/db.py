import os
from collections.abc import Iterator

from sqlalchemy.orm import Session, sessionmaker

from models import make_engine

# CH12_ECHO=1 logs every SQL statement.
engine = make_engine(echo=os.environ.get("CH12_ECHO") == "1")
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """One session per request, closed when the response is sent."""
    with SessionLocal() as session:
        yield session
