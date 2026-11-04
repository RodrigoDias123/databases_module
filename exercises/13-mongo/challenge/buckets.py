"""Challenge 13: buckets.py

Guarda o histórico de alugueres de cada cliente de duas formas, a partir da
coleção `rentals` do exercício, e compara-as para o cliente 380:

- `rental_buckets`: no máximo 50 alugueres por documento (bucket pattern).
- `rental_history`: um documento por cliente com todos os alugueres embebidos.

Uso:
    uv run --env-file ../../../.env python buckets.py

Lê `MONGO_URL` do ambiente. A coleção `rentals` já tem de estar carregada
(`exercise/load.py`).
"""

import os
import statistics
import time

import bson
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

MONGO_DB = "pagila_docs"
MAX_RENTALS = 50
COMPARE_CUSTOMER_ID = 380
RECENT_RENTALS = 20
TIMING_RUNS = 500

client = MongoClient(os.environ["MONGO_URL"], tz_aware=True)
db = client[MONGO_DB]


def create_indexes():
    """Tarefa 2: cria os índices de que `add_rental` precisa para ser segura."""
    db.rental_buckets.create_index([("customer_id", 1), ("seq", 1)], unique=True)


def add_rental(customer_id, rental):
    """Tarefa 2: adiciona `rental` ao bucket aberto do cliente ou abre um novo.

    Usa um único `update_one` com `upsert=True` e um filtro em `count`.
    """
    while True:
        # Só serve para o `seq` de um bucket novo. A segurança vem do filtro em
        # `count` e do índice único: se este valor estiver desatualizado, o
        # índice rejeita o insert e tenta-se outra vez.
        seq = db.rental_buckets.count_documents({"customer_id": customer_id})
        try:
            db.rental_buckets.update_one(
                {"customer_id": customer_id, "count": {"$lt": MAX_RENTALS}},
                {
                    "$push": {"rentals": rental},
                    "$inc": {"count": 1},
                    "$setOnInsert": {"seq": seq},
                },
                upsert=True,
            )
            return
        except DuplicateKeyError:
            continue


def load_buckets():
    """Tarefa 3: enche `rental_buckets` a partir de `rentals`, por `rental_date`."""
    for rental in db.rentals.find({}).sort([("rental_date", 1), ("_id", 1)]):
        add_rental(rental["customer_id"], rental)


def check_buckets():
    """Tarefa 3: confirma o limite de 50 e os buckets do cliente de comparação."""
    largest = db.rental_buckets.find_one(sort=[("count", -1)])
    print(f"rental_buckets: {db.rental_buckets.count_documents({})} documentos")
    print(f"maior bucket: {largest['count']} alugueres")

    rentals_in_buckets = db.rental_buckets.aggregate(
        [{"$group": {"_id": None, "total": {"$sum": "$count"}}}]
    ).next()["total"]
    print(f"alugueres nos buckets: {rentals_in_buckets} (rentals: {db.rentals.count_documents({})})")

    counts = [
        bucket["count"]
        for bucket in db.rental_buckets.find({"customer_id": COMPARE_CUSTOMER_ID}).sort("seq", 1)
    ]
    print(f"cliente {COMPARE_CUSTOMER_ID}: buckets com {counts} alugueres")


def build_history():
    """Tarefa 4: cria `rental_history`, um documento por cliente com todos os alugueres."""
    db.rentals.aggregate(
        [
            {"$sort": {"customer_id": 1, "rental_date": 1, "_id": 1}},
            {"$group": {"_id": "$customer_id", "rentals": {"$push": "$$ROOT"}}},
            {"$out": "rental_history"},
        ]
    )
    print(f"rental_history: {db.rental_history.count_documents({})} documentos")


def recent_from_buckets(customer_id, limit):
    """Lê os buckets do mais recente para o mais antigo e para quando tem `limit`."""
    rentals = []
    # `batch_size(1)`: sem isto, o driver traz logo vários buckets no primeiro lote.
    cursor = (
        db.rental_buckets.find({"customer_id": customer_id}, {"rentals": {"$slice": -limit}})
        .sort("seq", -1)
        .batch_size(1)
    )
    with cursor:
        for bucket in cursor:
            rentals = bucket["rentals"] + rentals
            if len(rentals) >= limit:
                break
    return rentals[-limit:][::-1]


def recent_from_history(customer_id, limit):
    """Lê o único documento do cliente e devolve só os últimos `limit` alugueres."""
    doc = db.rental_history.find_one({"_id": customer_id}, {"rentals": {"$slice": -limit}})
    return doc["rentals"][::-1]


def median_ms(read, customer_id, limit):
    """Mediana, em milissegundos, de `TIMING_RUNS` leituras à base de dados."""
    times = []
    for _ in range(TIMING_RUNS):
        start = time.perf_counter()
        read(customer_id, limit)
        times.append((time.perf_counter() - start) * 1000)
    return statistics.median(times)


def compare():
    """Tarefa 5: compara as duas coleções para `COMPARE_CUSTOMER_ID`.

    `len(bson.encode(doc))` dá o mesmo valor que `$bsonSize` no servidor. No mongosh
    2.13 `Object.bsonsize` não existe; a função disponível é `bsonsize`.
    """
    customer_id = COMPARE_CUSTOMER_ID

    for bucket in db.rental_buckets.find({"customer_id": customer_id}).sort("seq", 1):
        print(f"bucket seq {bucket['seq']} ({bucket['count']} alugueres): {len(bson.encode(bucket))} bytes")
    history_doc = db.rental_history.find_one({"_id": customer_id})
    print(f"rental_history ({len(history_doc['rentals'])} alugueres): {len(bson.encode(history_doc))} bytes")

    from_buckets = recent_from_buckets(customer_id, RECENT_RENTALS)
    from_history = recent_from_history(customer_id, RECENT_RENTALS)
    same = [r["_id"] for r in from_buckets] == [r["_id"] for r in from_history]
    print(f"{RECENT_RENTALS} mais recentes iguais nas duas coleções: {same}")

    print(f"leitura em rental_buckets: {median_ms(recent_from_buckets, customer_id, RECENT_RENTALS):.3f} ms (mediana)")
    print(f"leitura em rental_history: {median_ms(recent_from_history, customer_id, RECENT_RENTALS):.3f} ms (mediana)")


def main():
    # `add_rental` não é idempotente: recomeçar evita duplicar alugueres.
    db.rental_buckets.drop()
    db.rental_history.drop()

    create_indexes()
    load_buckets()
    check_buckets()
    build_history()
    compare()


if __name__ == "__main__":
    main()
