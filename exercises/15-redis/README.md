# Exercício 15: Redis I, data structures and patterns

## Enunciado

Folder: `exercises/15-redis/exercise/`

**Goal.** Implement four common Redis patterns on Pagila data and show each one working.

**Starting point.** A fresh copy of Pagila and a uv project. The scripts read `DATABASE_URL` and `REDIS_URL` from the environment (see `.env.example`).

```bash
./scripts/create-db.sh ex15 --pagila --reset
uv init --bare
uv add redis "psycopg[binary]"
```

Create this materialised view in `ex15` (it is the one of exercise 06):

```sql
CREATE MATERIALIZED VIEW monthly_revenue AS
SELECT date_trunc('month', payment_date)::date AS month, sum(amount) AS revenue
FROM payment
GROUP BY 1;

CREATE UNIQUE INDEX ON monthly_revenue (month);
```

**Tasks.** Put the functions in `patterns.py` and the demonstrations in `demo.py`, which prints what happens at each step.

1. Recently viewed films. `record_view(customer_id, film_id)` adds the film to the sorted set `customer:{customer_id}:viewed` with the current time as score, keeps only the 20 most recent, and sets the key to expire 30 days after the last view. `recent_views(customer_id)` returns the film IDs, most recent first. Demonstration: customer 1 views films 1 to 25 in order; `recent_views(1)` returns films 25 down to 6; viewing film 10 again moves it to the front without duplicating it; `TTL` is close to 2,592,000 seconds.
2. Cache-aside. `get_film(film_id)` reads `cache:film:{film_id}` (JSON with `title`, `rating`, `length` and `rental_rate`); on a miss it reads PostgreSQL and stores the result for 300 seconds. `update_film_rate(film_id, rate)` updates PostgreSQL and deletes the cache key. Demonstration for film 1: the first `get_film` is a miss, the second a hit, then `update_film_rate(1, 1.99)`, and the next `get_film` is a miss that returns 1.99.
3. Lock. `refresh.py` takes the lock `lock:refresh:monthly_revenue` with `SET ... NX EX 60` and a random token, runs `REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_revenue`, waits 5 seconds while still holding the lock (so that the overlap is visible), and releases the lock with a Lua script that deletes it only if it still holds the token. Demonstration: start two processes at the same time (`uv run python refresh.py & uv run python refresh.py & wait`); one prints that it refreshed, the other that it skipped because the lock was held.
4. Rate limit. `allow_request(customer_id)` allows 10 requests per customer per minute, with a counter per customer per minute that expires. Demonstration: 12 calls in a row for customer 1 give 10 `True` and 2 `False`; after the next minute starts, a call gives `True` again.

**Deliverables.**

- `patterns.py`, `demo.py`, `refresh.py`, `pyproject.toml`.
- `README.md` with the commands, the output of `demo.py` and of the two `refresh.py` processes, and a table of every key pattern you use with its Redis type, TTL and purpose.

**Done when.** Every demonstration shows the expected result, and the lock is never released by a process that does not hold it.

## Challenge (opcional, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [ ] Recently viewed films: sorted set, 20 most recent, 30-day TTL
- [ ] Cache-aside for film details with TTL, invalidated on update
- [ ] `refresh.py`: lock with token and Lua release, two processes, only one refreshes
- [ ] Rate limit: 10 requests per customer per minute
- [ ] Table of key patterns with type, TTL and purpose
