# Challenge 04: CRUD, upsert and bulk data

Obrigatório.

## Enunciado

Write a Python seed script that adds 1 million rentals to Pagila in under 30 seconds, using `COPY`. Every row must be valid: existing inventory, customer and staff IDs, and a return date after the rental date. Run it twice on fresh copies of Pagila and prove the data is identical both times (for example, compare `md5(string_agg(...))` over the table ordered by primary key). Make the script idempotent: running it again on a database that already has the data must not create duplicates.
