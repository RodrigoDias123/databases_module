# Exercício 16: Redis II, source of truth, rebuild and persistence

## Enunciado

Folder: `exercises/16-consistency/exercise/`

**Goal.** Treat Redis as derived data: rebuild it from PostgreSQL, verify it, and choose its persistence.

**Starting point.** A fresh copy of Pagila and a uv project:

```bash
./scripts/create-db.sh ex16 --pagila --reset
uv init --bare
uv add redis "psycopg[binary]"
```

Use Redis logical database 1 for this exercise (end `REDIS_URL` with `/1`), so that `FLUSHDB` there does not delete the keys of other exercises.

**Tasks.**

1. `rebuild.py` creates, for every customer with rentals, the set `customer:{customer_id}:categories` with the names of the categories of every film the customer has rented (a film can have several categories). It reads PostgreSQL with one query and writes Redis with one pipeline. Each set is built in a temporary key and renamed at the end, so that readers never see a half-built set. Expected: 997 sets (customers 647 and 978 have no rentals).
2. Run `FLUSHDB` on database 1, run `rebuild.py`, and count the keys with `SCAN` (not `KEYS`).
3. `verify.py` compares every set with PostgreSQL, size and members, and also reports any `customer:*:categories` key for a customer who should not have one. It prints every difference and exits with 1 if there is any, 0 otherwise. Show it exiting with 1 after `SREM customer:1:categories Action`, with 1 after `SADD customer:647:categories Fake`, and with 0 after running `rebuild.py` again.
4. Fill a table for every key pattern of exercises 15 and 16 (viewed films, film cache, lock, rate limit, categories) with: its class (source of truth, derived or ephemeral), what is lost if Redis loses it, and how it comes back.
5. Choose one configuration for the Redis instance (`appendonly`, `appendfsync`, `maxmemory`, `maxmemory-policy`) and justify it against the table of task 4. `maxmemory-policy` applies to the whole instance, not to one key, so explain the trade-off and when you would use two Redis instances instead. `docker-compose.redis-aof.yml` in this repository turns on AOF; read the warning in `sessions/16-redis-consistency/` before using it.

**Deliverables.**

- `rebuild.py`, `verify.py`, `pyproject.toml`.
- `README.md` with the commands, the output of tasks 2 and 3, the table of task 4, and the configuration and justification of task 5.

**Done when.** The rebuild creates 997 sets in one query and one pipeline, `verify.py` detects both changes and passes after the rebuild, and every choice in tasks 4 and 5 is justified.

## Challenge (opcional, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [ ] `rebuild.py`: 997 sets, one query, one pipeline, temporary key + rename
- [ ] `FLUSHDB` + rebuild + count with `SCAN`
- [ ] `verify.py`: exits 1 after `SREM` and after `SADD` on customer 647, 0 after rebuild
- [ ] Table of every key pattern of ex. 15 and 16: class, what is lost, how it comes back
- [ ] Redis configuration (`appendonly`, `appendfsync`, `maxmemory`, `maxmemory-policy`) justified
