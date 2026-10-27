"""Cria as tabelas das duas bases a partir dos modelos em app/models/.

Cada base tem a sua Base (e o seu metadata), para create_all só criar as tabelas certas
em cada uma. Correr `python -m app.schema` cria as tabelas que ainda não existem.
"""

from app.connection import pg1_engine, pg2_engine
from app.models import Pg1Base, Pg2Base


def create_schema():
    """Cria as tabelas que faltam nas duas bases (as que já existem não são alteradas)."""
    Pg1Base.metadata.create_all(pg1_engine)
    Pg2Base.metadata.create_all(pg2_engine)


if __name__ == "__main__":
    create_schema()
