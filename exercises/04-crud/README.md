# Exercício 04: CRUD, upsert and bulk data

## Enunciado

Folder: `exercises/04-crud/queries.sql`

12 operations on Pagila, with the expected result (row count or value) given in the brief. Examples: films rated `PG-13` and longer than 120 minutes sorted by title; customers with no rentals in the last year; update the rental rate of one category using `RETURNING`; upsert an actor; delete test payments after checking the `WHERE` first.

Marked 2 for 11 or 12 correct, 1 for 6 to 10.

Group project: complete DDL for your scenario and start the seed with volume.

## Challenge (opcional, em `challenge/`)

Write a Python seed script that adds 1 million rentals to Pagila in under 30 seconds, using `COPY`. Every row must be valid: existing inventory, customer and staff IDs, and a return date after the rental date. Run it twice on fresh copies of Pagila and prove the data is identical both times (for example, compare `md5(string_agg(...))` over the table ordered by primary key). Make the script idempotent: running it again on a database that already has the data must not create duplicates.
