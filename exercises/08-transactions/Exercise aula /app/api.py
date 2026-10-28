"""API HTTP do Generator Service (FastAPI).

    POST /generate              processa as tasks pendentes (PG1 -> PG2) e devolve o resultado de cada uma
    GET  /tasks                 lista os pedidos da PG1 (filtro opcional ?status=pendente)
    GET  /tasks/{id}            estado de um pedido
    GET  /tasks/{id}/reports    relatórios gerados na PG2 para esse pedido

Arranque: `uvicorn app.api:app --host 0.0.0.0 --port 8000` (o serviço `api` do compose).
Documentação interativa em /docs.

Os endpoints são `def` (não `async def`): o SQLAlchemy é síncrono e o FastAPI corre-os numa
threadpool. Dois POST /generate em simultâneo não processam a mesma task, graças ao SKIP LOCKED
em claim_tasks.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.connection import get_pg1_session, get_pg2_session
from app.generator import generate_report
from app.schema import create_schema

TASK_COLUMNS = "id, dt, nome, status, outcome, finished"


@asynccontextmanager
async def lifespan(app):
    """Cria as tabelas que faltam antes de aceitar pedidos."""
    create_schema()
    yield


app = FastAPI(title="Generator Service", lifespan=lifespan)


@app.post("/generate")
def generate():
    """Processa todas as tasks pendentes."""
    results = generate_report()
    return {"processed": len(results), "tasks": results}


@app.get("/tasks")
def list_tasks(status: str | None = None):
    """Lista os pedidos, opcionalmente filtrados pelo estado."""
    with get_pg1_session() as pg1:
        return pg1.execute(
            text(f"""
                SELECT {TASK_COLUMNS} FROM tasks_req
                WHERE CAST(:status AS text) IS NULL OR status = :status
                ORDER BY id
            """),
            {"status": status},
        ).mappings().all()


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Estado de um pedido."""
    with get_pg1_session() as pg1:
        task = pg1.execute(
            text(f"SELECT {TASK_COLUMNS} FROM tasks_req WHERE id = :task_id"),
            {"task_id": task_id},
        ).mappings().one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} não existe")
    return task


@app.get("/tasks/{task_id}/reports")
def get_task_reports(task_id: int):
    """Relatórios de um pedido. A PG2 não tem task_id, por isso filtra pelo JSON do conteúdo."""
    get_task(task_id)  # 404 se a task não existir
    with get_pg2_session() as pg2:
        return pg2.execute(
            text("""
                SELECT r.id_ppt, r.dt, c.content
                FROM insight_report r
                JOIN report_content c ON c.id = r.report_content_id
                WHERE (c.content -> 'task' ->> 'id')::bigint = :task_id
                ORDER BY r.id_ppt, r.dt
            """),
            {"task_id": task_id},
        ).mappings().all()
