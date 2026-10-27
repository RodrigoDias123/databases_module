"""Gera data/participants.json com dados falsos (Faker, locale pt_PT), no formato que a ingestão lê.

Cada pedido é um rastreio num distrito, com participantes desse distrito. Os distritos não se
repetem até serem usados os 18; só aí recomeçam. Os valores de saúde
seguem distribuições plausíveis: a altura depende do sexo, o peso sai de um IMC aleatório e a
pressão arterial sobe com a idade, para o relatório ter todas as categorias.

O Faker é dependência de desenvolvimento, por isso isto corre fora do container (o ./data
é copiado para a imagem no build):

    uv run python -m app.fake_data --tasks 5 --seed 42
"""

import argparse
import json
import logging
from datetime import date
from pathlib import Path

from faker import Faker
from faker.exceptions import UniquenessException

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "participants.json"


def fake_participant(fake, distrito, today):
    """Um participante com valores de saúde coerentes entre si."""
    rnd = fake.random
    female = rnd.random() < 0.5
    dnasc = fake.date_of_birth(minimum_age=18, maximum_age=90)
    idade = today.year - dnasc.year

    alt = rnd.gauss(1.62, 0.06) if female else rnd.gauss(1.75, 0.07)
    imc = min(max(rnd.gauss(26, 4), 17), 42)
    bp_sys = round(rnd.gauss(98 + 0.5 * idade, 11))
    bp_dia = round(rnd.gauss(62 + 0.2 * idade, 7))

    return {
        "nome": fake.name_female() if female else fake.name_male(),
        "localidade": distrito,
        "dnasc": dnasc.isoformat(),
        "alt": round(alt, 2),
        "peso": round(imc * alt**2, 1),
        "bp_sys": min(max(bp_sys, 90), 200),
        "bp_dia": min(max(bp_dia, 55), 120),
        "hr": min(max(round(rnd.gauss(72, 10)), 45), 120),
    }


def fake_tasks(n_tasks, min_ppt, max_ppt, seed=None):
    """Lista de pedidos, cada um com entre min_ppt e max_ppt participantes."""
    fake = Faker("pt_PT")
    if seed is not None:
        fake.seed_instance(seed)
    today = date.today()

    tasks = []
    for _ in range(n_tasks):
        try:
            distrito = fake.unique.distrito()
        except UniquenessException:
            fake.unique.clear()
            distrito = fake.unique.distrito()
        n = fake.random_int(min_ppt, max_ppt)
        tasks.append({
            "nome": f"Rastreio {distrito}",
            "participants": [fake_participant(fake, distrito, today) for _ in range(n)],
        })
    return tasks


def main():
    """Gera o ficheiro JSON a partir dos argumentos da linha de comandos."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tasks", type=int, default=5, help="número de pedidos (default: 5)")
    parser.add_argument("--min", type=int, default=3, help="mínimo de participantes por pedido (default: 3)")
    parser.add_argument("--max", type=int, default=10, help="máximo de participantes por pedido (default: 10)")
    parser.add_argument("--seed", type=int, help="seed para gerar sempre os mesmos dados")
    parser.add_argument("--output", type=Path, default=DATA_FILE, help=f"ficheiro de saída (default: {DATA_FILE})")
    args = parser.parse_args()

    tasks = fake_tasks(args.tasks, args.min, args.max, args.seed)
    args.output.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    n_participants = sum(len(t["participants"]) for t in tasks)
    log.info("Gerados %d pedido(s) e %d participante(s) em %s", len(tasks), n_participants, args.output)


if __name__ == "__main__":
    main()
