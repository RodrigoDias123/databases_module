"""Generator Service: lê as tasks pendentes da PG1, gera o relatório em JSON e escreve-o na PG2.

Fluxo de cada task (as duas bases não partilham transações, por isso o estado em tasks_req
é o que permite saber onde cada pedido ficou):

    pendente ──> em curso ──> concluído
                         └──> erro
"""

import json
import logging
from datetime import date

from sqlalchemy import text

from app.connection import get_pg1_session, get_pg2_session

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def claim_tasks(pg1):
    """Passa as tasks pendentes a 'em curso' e devolve-as.

    SKIP LOCKED garante que dois generators em paralelo não apanham a mesma task.
    """
    with pg1.begin():
        return pg1.execute(text("""
            UPDATE tasks_req SET status = 'em curso'
            WHERE id IN (
                SELECT id FROM tasks_req
                WHERE status = 'pendente'
                ORDER BY dt
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, nome
        """)).all()


def read_participants(pg1, task_id):
    """Lê os participantes de uma task."""
    with pg1.begin():
        return pg1.execute(
            text("""
                SELECT id, nome, localidade, dnasc, alt, peso, bp_sys, bp_dia, hr
                FROM participant
                WHERE task_id = :task_id
                ORDER BY id
            """),
            {"task_id": task_id},
        ).mappings().all()


def age(dnasc, today):
    """Idade em anos completos."""
    return today.year - dnasc.year - ((today.month, today.day) < (dnasc.month, dnasc.day))


def bp_category(sys, dia):
    """Classificação da pressão arterial (escala da AHA)."""
    if sys >= 140 or dia >= 90:
        return "hipertensão grau 2"
    if sys >= 130 or dia >= 80:
        return "hipertensão grau 1"
    if sys >= 120:
        return "elevada"
    return "normal"


def build_content(task, ppt, today):
    """Conteúdo do relatório (JSON) de um participante. alt em metros, peso em kg."""
    alt = float(ppt["alt"])
    peso = float(ppt["peso"])
    return {
        "task": {"id": task.id, "nome": task.nome},
        "participant": {
            "id": ppt["id"],
            "nome": ppt["nome"],
            "localidade": ppt["localidade"],
            "idade": age(ppt["dnasc"], today),
        },
        "imc": round(peso / alt**2, 1),
        "pressao_arterial": {
            "sys": ppt["bp_sys"],
            "dia": ppt["bp_dia"],
            "categoria": bp_category(ppt["bp_sys"], ppt["bp_dia"]),
        },
        "hr": ppt["hr"],
    }


def write_reports(pg2, contents):
    """Grava os relatórios de uma task na PG2, numa só transação (todos ou nenhum)."""
    with pg2.begin():
        for content in contents:
            content_id = pg2.execute(
                text("INSERT INTO report_content (content) VALUES (CAST(:content AS jsonb)) RETURNING id"),
                {"content": json.dumps(content, ensure_ascii=False)},
            ).scalar_one()
            pg2.execute(
                text("INSERT INTO insight_report (id_ppt, report_content_id) VALUES (:id_ppt, :content_id)"),
                {"id_ppt": content["participant"]["id"], "content_id": content_id},
            )


def finish_task(pg1, task_id, status, outcome):
    """Fecha a task com o estado final, o resultado e a hora de conclusão."""
    with pg1.begin():
        pg1.execute(
            text("""
                UPDATE tasks_req
                SET status = :status, outcome = :outcome, finished = now()
                WHERE id = :task_id
            """),
            {"status": status, "outcome": outcome[:255], "task_id": task_id},
        )


def generate_report():
    """Processa todas as tasks pendentes. Devolve o resultado de cada uma (id, nome, status, outcome)."""
    today = date.today()
    results = []

    with get_pg1_session() as pg1, get_pg2_session() as pg2:
        tasks = claim_tasks(pg1)
        log.info("%d task(s) pendente(s)", len(tasks))

        for task in tasks:
            try:
                participants = read_participants(pg1, task.id)
                contents = [build_content(task, ppt, today) for ppt in participants]
                write_reports(pg2, contents)
            except Exception as e:
                log.exception("Task %d falhou", task.id)
                status, outcome = "erro", f"{type(e).__name__}: {e}"
            else:
                status, outcome = "concluído", f"{len(contents)} relatório(s) gerado(s)"
                log.info("Task %d concluída: %d relatório(s)", task.id, len(contents))
            finish_task(pg1, task.id, status, outcome)
            results.append({"id": task.id, "nome": task.nome, "status": status, "outcome": outcome[:255]})

        return results


def main():
    """Função principal do serviço de geração de relatórios."""
    generate_report()


if __name__ == "__main__":
    main()
