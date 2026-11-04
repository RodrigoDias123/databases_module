"""Tarefa 1: load.py

Lê o Pagila (PostgreSQL) e escreve as coleções `films`, `customers` e `rentals`
na base MongoDB `pagila_docs`.

Uso:
    uv run --env-file ../../../.env python load.py

Lê `DATABASE_URL` (base ex13) e `MONGO_URL` do ambiente. Cada documento é
escrito com `ReplaceOne(..., upsert=True)` e o `_id` é o ID do Pagila, por isso
correr o script duas vezes deixa os mesmos documentos.
"""

import os
from decimal import Decimal

import psycopg
from bson.decimal128 import Decimal128
from psycopg.rows import dict_row
from pymongo import MongoClient, ReplaceOne

MONGO_DB = "pagila_docs"
RECENT_RENTALS = 10
BATCH_SIZE = 5000

FILMS_SQL = """
SELECT f.film_id, f.title, f.release_year, l.name AS language, f.rating::text AS rating,
       f.length, f.rental_duration, f.rental_rate,
       coalesce((SELECT array_agg(c.name ORDER BY c.name)
                 FROM film_category fc JOIN category c USING (category_id)
                 WHERE fc.film_id = f.film_id), '{}') AS categories,
       coalesce((SELECT json_agg(json_build_object('actor_id', a.actor_id,
                                                   'name', a.first_name || ' ' || a.last_name)
                                 ORDER BY a.actor_id)
                 FROM film_actor fa JOIN actor a USING (actor_id)
                 WHERE fa.film_id = f.film_id), '[]') AS actors
FROM film f
JOIN language l USING (language_id)
ORDER BY f.film_id
"""

CUSTOMERS_SQL = """
SELECT cu.customer_id, cu.first_name, cu.last_name, cu.email, cu.store_id,
       ci.city, co.country,
       (SELECT count(*) FROM rental r WHERE r.customer_id = cu.customer_id) AS rental_count
FROM customer cu
JOIN address a USING (address_id)
JOIN city ci USING (city_id)
JOIN country co USING (country_id)
ORDER BY cu.customer_id
"""

RECENT_RENTALS_SQL = """
SELECT customer_id, rental_id, film_id, title, rental_date, return_date
FROM (
    SELECT r.customer_id, r.rental_id, i.film_id, f.title, r.rental_date, r.return_date,
           row_number() OVER (PARTITION BY r.customer_id
                              ORDER BY r.rental_date DESC, r.rental_id DESC) AS n
    FROM rental r
    JOIN inventory i USING (inventory_id)
    JOIN film f USING (film_id)
) recent
WHERE n <= %s
ORDER BY customer_id, n
"""

RENTALS_SQL = """
WITH paid AS (
    SELECT rental_id, sum(amount) AS amount
    FROM payment
    GROUP BY rental_id
)
SELECT r.rental_id, r.customer_id, i.film_id, f.title, i.store_id,
       r.rental_date, r.return_date, coalesce(paid.amount, 0) AS amount
FROM rental r
JOIN inventory i USING (inventory_id)
JOIN film f USING (film_id)
LEFT JOIN paid USING (rental_id)
ORDER BY r.rental_id
"""

FILM_CATEGORIES_SQL = """
SELECT fc.film_id, array_agg(c.name ORDER BY c.name) AS categories
FROM film_category fc
JOIN category c USING (category_id)
GROUP BY fc.film_id
"""


def money(value):
    return Decimal128(Decimal(value))


def film_docs(conn):
    for row in conn.execute(FILMS_SQL):
        yield {
            "_id": row["film_id"],
            "title": row["title"],
            "release_year": row["release_year"],
            "language": row["language"].strip(),
            "rating": row["rating"],
            "length": row["length"],
            "rental_duration": row["rental_duration"],
            "rental_rate": money(row["rental_rate"]),
            "categories": list(row["categories"]),
            "actors": row["actors"],
        }


def customer_docs(conn):
    recent = {}
    for row in conn.execute(RECENT_RENTALS_SQL, (RECENT_RENTALS,)):
        recent.setdefault(row["customer_id"], []).append({
            "rental_id": row["rental_id"],
            "film_id": row["film_id"],
            "title": row["title"],
            "rental_date": row["rental_date"],
            "return_date": row["return_date"],
        })

    for row in conn.execute(CUSTOMERS_SQL):
        yield {
            "_id": row["customer_id"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "email": row["email"],
            "store_id": row["store_id"],
            "address": {"city": row["city"], "country": row["country"]},
            "rental_count": row["rental_count"],
            "recent_rentals": recent.get(row["customer_id"], []),
        }


def rental_docs(conn):
    categories = {
        row["film_id"]: list(row["categories"])
        for row in conn.execute(FILM_CATEGORIES_SQL)
    }
    for row in conn.execute(RENTALS_SQL):
        yield {
            "_id": row["rental_id"],
            "customer_id": row["customer_id"],
            "film_id": row["film_id"],
            "title": row["title"],
            "categories": categories.get(row["film_id"], []),
            "store_id": row["store_id"],
            "rental_date": row["rental_date"],
            "return_date": row["return_date"],
            "amount": money(row["amount"]),
        }


def upsert_all(collection, docs):
    batch = []
    for doc in docs:
        batch.append(ReplaceOne({"_id": doc["_id"]}, doc, upsert=True))
        if len(batch) == BATCH_SIZE:
            collection.bulk_write(batch, ordered=False)
            batch = []
    if batch:
        collection.bulk_write(batch, ordered=False)


def main():
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn, \
            MongoClient(os.environ["MONGO_URL"], tz_aware=True) as client:
        db = client[MONGO_DB]
        upsert_all(db.films, film_docs(conn))
        upsert_all(db.customers, customer_docs(conn))
        upsert_all(db.rentals, rental_docs(conn))

        for name in ("films", "customers", "rentals"):
            print(f"{name}: {db[name].count_documents({})}")


if __name__ == "__main__":
    main()
