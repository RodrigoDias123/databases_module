# Exercício 04: CRUD, upsert and bulk data

## Enunciado

Folder: `exercises/04-crud/exercise/`

**Goal.** Read, insert, update and delete data safely, and use upsert.

**Starting point.** A fresh copy of Pagila:

```bash
./scripts/create-db.sh ex04 --pagila --reset
```

The expected results below assume the operations run in this order on a fresh copy.

**Tasks.** Write one statement (or one short transaction) per operation:

1. Films rated `PG-13` and longer than 120 minutes, sorted by title. Expected: 118 rows, from `APOLLO TEEN` to `WRONG BEHAVIOR`.
2. Actors whose last name contains `son`, in any case. Expected: 9 rows.
3. Rentals that have not been returned yet. Expected: 241 rows.
4. The distinct values of `rental_duration` in `film`, in ascending order. Expected: 5 rows, `3` to `7`.
5. The third page of films ordered by title, 10 films per page. Expected: 10 rows, from `AMERICAN CIRCUS` to `ANYTHING SAVANNAH`.
6. The number of rentals made in January 2026, written twice: with `rental_date BETWEEN '2026-01-01' AND '2026-01-31'`, and with `rental_date >= '2026-01-01' AND rental_date < '2026-02-01'`. Expected: 746 and 781. Explain in a comment why they differ and which one is correct.
7. Insert the actor `ADA LOVELACE` and get the generated `actor_id` back with `RETURNING`. Expected: 1 row with `actor_id` 201.
8. In a transaction, raise the `rental_rate` of films rated `NC-17` and shorter than 60 minutes by 0.50. First run a `SELECT count(*)` with the same `WHERE`, then the `UPDATE ... RETURNING film_id, title, rental_rate`, then `COMMIT`. Expected: 21 rows in both.
9. Create the table below, then write an upsert that adds one award to actor 1 (insert with 1, or add 1 if the row exists). Run it twice. Expected: `awards` is 2.

   ```sql
   CREATE TABLE actor_award (
       actor_id integer PRIMARY KEY REFERENCES actor,
       awards   integer NOT NULL DEFAULT 0
   );
   ```

10. Insert actor 2 with 5 awards using `ON CONFLICT DO NOTHING`, and run it twice. Expected: the first run inserts 1 row, the second inserts 0 rows.
11. Insert 3 test payments in one statement: `customer_id` 1, `staff_id` 2, `rental_id` 76, `amount` 0.01, `payment_date` `'2026-07-30 12:00+00'`. Return their `payment_id` with `RETURNING`. Expected: 3 rows.
12. Delete the 3 test payments. First run a `SELECT count(*)` with the `WHERE` you will use, then the `DELETE ... RETURNING`, inside a transaction. Expected: 3 rows in both.

**Deliverables.**

- `queries.sql` with the 12 operations, numbered with a comment (`-- 1.`, `-- 2.`, ...).
- `README.md` with the output of each operation (for long results, the row count and the first and last rows).

**Done when.** `queries.sql` runs from top to bottom on a fresh copy with `ON_ERROR_STOP=1` and every result matches the expected one.

## Challenge (obrigatório, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [ ] `queries.sql` with the 12 operations, numbered `-- 1.` to `-- 12.`
- [ ] Runs from top to bottom on a fresh copy (`ex04`) with `ON_ERROR_STOP=1`
- [ ] Every result matches the expected one
- [ ] Task 6: comment explaining why the two counts differ and which one is correct
- [ ] `README.md` with the output of each operation

## Resposta

Resposta em [exercise/README.md](exercise/README.md).
