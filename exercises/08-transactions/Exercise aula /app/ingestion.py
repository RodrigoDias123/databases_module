"""Data ingestion: JSON -> PG1.

O ficheiro é uma lista de pedidos, cada um com os seus participantes:

    [{"nome": "...", "participants": [{"nome": "...", "localidade": "...", "dnasc": "AAAA-MM-DD",
                                        "alt": 1.70, "peso": 70.0, "bp_sys": 120, "bp_dia": 80,
                                        "hr": 70}, ...]}, ...]

Cada pedido entra em tasks_req como 'pendente', para o Generator Service o apanhar.
"""

import json
import logging
import os
from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.connection import get_pg1_session

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Relativo a WORKDIR /app no container, onde o compose monta ./data.
DATA_FILE = os.getenv("DATA_FILE", "data/participants.json")


def load_tasks(path):
    """Lê o JSON. Decimal evita arredondamentos de float em alt e peso."""
    with open(path, encoding="utf-8") as f:
        return json.load(f, parse_float=Decimal)


def ingest_data(path=DATA_FILE):
    """Insere os pedidos e participantes do ficheiro na PG1. Devolve o número de pedidos."""
    tasks = load_tasks(path)

    # Uma só transação para o ficheiro todo: se uma linha falhar, não fica nada a meio.
    with get_pg1_session() as pg1, pg1.begin():
        n_participants = 0
        for task in tasks:
            task_id = pg1.execute(
                text("INSERT INTO tasks_req (nome, status) VALUES (:nome, 'pendente') RETURNING id"),
                {"nome": task["nome"]},
            ).scalar_one()

            for ppt in task["participants"]:
                pg1.execute(
                    text("""
                        INSERT INTO participant
                            (nome, localidade, dnasc, alt, peso, bp_sys, bp_dia, hr, task_id)
                        VALUES
                            (:nome, :localidade, :dnasc, :alt, :peso, :bp_sys, :bp_dia, :hr, :task_id)
                    """),
                    {**ppt, "dnasc": date.fromisoformat(ppt["dnasc"]), "task_id": task_id},
                )
            n_participants += len(task["participants"])

    log.info("Ingeridos %d pedido(s) e %d participante(s) de %s", len(tasks), n_participants, path)
    return len(tasks)


if __name__ == "__main__":
    ingest_data()
