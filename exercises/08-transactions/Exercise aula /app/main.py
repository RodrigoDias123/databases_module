"""Corre o pipeline completo: cria as tabelas, faz a ingestão e depois o Generator Service."""

import logging

from app.generator import generate_report
from app.ingestion import ingest_data
from app.schema import create_schema

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def main():
    """Função principal do pipeline completo."""
    log.info("A iniciar o pipeline...")
    create_schema()
    ingest_data()
    generate_report()
    log.info("Pipeline concluído.")


if __name__ == "__main__":
    main()
