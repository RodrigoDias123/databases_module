# Exercício 12: ORM II, migrations, transactions and API

## Enunciado

Folder: `exercises/12-api/`

1. Alembic: initial migration of Pagila, a migration that adds a `NOT NULL` column with a default to a table with data, and proof that `downgrade` works.
2. An API with 3 endpoints: rent a film (with `with_for_update()` and `409` if no copy is available), return a film, list overdue rentals without N+1.

Marked 2 when the migrations are reversible and the 3 endpoints are correct.

Group project: initial migration of your scenario and an API with the main flows, including the critical transaction.

## Challenge (obrigatório, em `challenge/`)

Rename a column used by the API with zero downtime, using the expand and contract pattern across three migrations: (1) add the new column and keep both in sync with a trigger, (2) switch the code to the new column and backfill, (3) drop the old column and the trigger. Show that at every step both the old and the new version of the API work against the database.

## Checklist

- [ ] Alembic: initial migration of Pagila
- [ ] Migration adding a NOT NULL column with a default to a table with data
- [ ] Proof that downgrade works
- [ ] Endpoint: rent a film (with_for_update(), 409 if no copy available)
- [ ] Endpoint: return a film
- [ ] Endpoint: list overdue rentals without N+1
