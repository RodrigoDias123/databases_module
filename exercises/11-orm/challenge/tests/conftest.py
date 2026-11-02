from contextlib import contextmanager

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from models import make_engine


@pytest.fixture(scope="session")
def engine():
    engine = make_engine()
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def statements(engine):
    """Every SQL statement the engine sends to the database while the test runs."""
    executed: list[str] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        executed.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    yield executed
    event.remove(engine, "before_cursor_execute", before_cursor_execute)


@pytest.fixture
def assert_max_queries(statements):
    """Context manager that fails the test if more than n statements ran inside the block."""

    @contextmanager
    def assert_max_queries(n: int):
        start = len(statements)
        yield
        ran = statements[start:]
        if len(ran) > n:
            first = "\n".join(f"  {i}. {s.splitlines()[0]} ..." for i, s in enumerate(ran[:5], 1))
            pytest.fail(
                f"expected at most {n} statements, {len(ran)} ran. First ones:\n{first}",
                pytrace=False,
            )

    return assert_max_queries
