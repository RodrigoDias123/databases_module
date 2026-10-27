"""Ligações às duas bases. Os DSN vêm das variáveis PG1_DSN e PG2_DSN (definidas no compose)."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _engine(env_var):
    """Cria o engine a partir do DSN, com o driver psycopg 3."""
    dsn = os.environ[env_var].replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(dsn)


# Um engine (e um pool de ligações) por base, criado uma só vez.
pg1_engine = _engine("PG1_DSN")
pg2_engine = _engine("PG2_DSN")

Pg1Session = sessionmaker(bind=pg1_engine)
Pg2Session = sessionmaker(bind=pg2_engine)


def get_pg1_session():
    """Cria uma sessão para a base PG1."""
    return Pg1Session()


def get_pg2_session():
    """Cria uma sessão para a base PG2."""
    return Pg2Session()
