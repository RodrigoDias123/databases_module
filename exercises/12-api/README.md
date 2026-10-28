# Exercício 12: ORM II, migrations, transactions and API

## Enunciado

Folder: `exercises/12-api/exercise/`

**Goal.** Evolve an existing schema with reversible migrations and expose a transactional API that stays correct under concurrent requests.

**Starting point.** A fresh copy of Pagila and a uv project:

```bash
./scripts/create-db.sh ex12 --pagila --reset
uv init --bare
uv add "sqlalchemy>=2" "psycopg[binary]" alembic fastapi "uvicorn[standard]" httpx
```

Map at least `customer`, `film`, `inventory`, `rental` and `staff`. You can reuse the models of exercise 11.

**Tasks.**

1. Baseline. Initialise Alembic, create a migration `0001_baseline` with empty `upgrade` and `downgrade`, and run `alembic stamp head` on `ex12`. Configure `include_object` in `migrations/env.py` so that `--autogenerate` ignores tables you did not map. In the README, explain what `--autogenerate` would have generated without the baseline and without `include_object`, and why that is dangerous.
2. Migration `0002_loyalty_points`: add `customer.loyalty_points integer NOT NULL`, filled with the customer's number of rentals, in three steps (add as nullable, fill, set `NOT NULL`), with `server_default` 0 for new rows. `downgrade` removes the column. Expected: customer 1 has 66 points.
3. Migration `0003_one_open_rental_per_copy`: three copies (`inventory_id` 1358, 1435 and 2408) have two open rentals each. Close the older open rental of each one by setting its `return_date` to the `rental_date` of the newer one, then create the partial unique index `rental_one_open_per_copy` on `rental (inventory_id) WHERE return_date IS NULL`. `downgrade` drops the index only. In the README, explain why the data fix is not undone.
4. Show `alembic upgrade head`, `alembic downgrade base` and `alembic upgrade head` again running without errors, with `\d customer` and `\d rental` after each.
5. An API with 3 endpoints, each request with its own session:
   - `POST /rentals` with body `{"customer_id": int, "film_id": int, "store_id": int, "staff_id": int}`. In one transaction, find a copy of the film in that store with no open rental, lock it with `with_for_update(skip_locked=True)` and insert the rental with `rental_date` now. Returns `201` with `rental_id` and `inventory_id`, `404` if the customer or the film does not exist, and `409` if no copy is available. If the insert violates `rental_one_open_per_copy` (another request rented the same copy between your read and your insert), retry the whole transaction, at most 3 times, before returning `409`.
   - `POST /rentals/{rental_id}/return` sets `return_date` to now. Returns `200`, `404` if the rental does not exist, and `409` if it was already returned.
   - `GET /rentals/overdue?as_of=2026-07-31` lists open rentals whose due date (`rental_date` plus the film's `rental_duration` in days) is before `as_of`, ordered by `rental_date`. Each item has `rental_id`, `rental_date`, `due_date`, `customer` (`customer_id`, `first_name`, `last_name`) and `film` (`film_id`, `title`). It must not have an N+1. Expected on a fresh copy after the migrations: 229 items.
6. `concurrency_test.py` sends 5 simultaneous `POST /rentals` for film 7 in store 1 (customers 1 to 5, staff 6). Film 7 has exactly 2 copies in store 1, both available on a fresh copy. Expected: exactly two `201` and three `409`, with two different `inventory_id`.

**Deliverables.**

- The project: models, `migrations/`, `app/`, `concurrency_test.py`, `pyproject.toml`.
- `README.md` with the commands to run the migrations, the API and the test, the output of tasks 4 and 6, the number of SQL statements `GET /rentals/overdue` runs (from the `echo=True` log), and the explanations asked in tasks 1 and 3.

**Done when.** The migrations go up, down and up again without errors, the endpoints return the status codes above, the overdue list has 229 items in a fixed number of queries, and the concurrency test gives two `201` and three `409` every time you run it on a fresh copy.

## Challenge (opcional, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [ ] `0001_baseline` + `alembic stamp head` + `include_object`, with explanation
- [ ] `0002_loyalty_points` (customer 1 has 66 points)
- [ ] `0003_one_open_rental_per_copy`, with explanation of why the data fix is not undone
- [ ] upgrade / downgrade base / upgrade with `\d customer` and `\d rental`
- [ ] `POST /rentals` (201/404/409, `skip_locked`, retries)
- [ ] `POST /rentals/{rental_id}/return` (200/404/409)
- [ ] `GET /rentals/overdue` (229 items, no N+1, number of statements)
- [ ] `concurrency_test.py`: two `201` and three `409`
