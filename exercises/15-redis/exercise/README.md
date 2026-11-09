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

- [x] Recently viewed films: sorted set, 20 most recent, 30-day TTL
- [x] Cache-aside for film details with TTL, invalidated on update
- [x] `refresh.py`: lock with token and Lua release, two processes, only one refreshes
- [x] Rate limit: 10 requests per customer per minute
- [x] Table of key patterns with type, TTL and purpose

## Resolução

Ficheiros entregues:

- [patterns.py](patterns.py): as quatro funções (`record_view`/`recent_views`, `get_film`/`update_film_rate`, `acquire_lock`/`release_lock`, `allow_request`).
- [demo.py](demo.py): demonstra cada padrão passo a passo.
- [refresh.py](refresh.py): refresh de `monthly_revenue` protegido pelo lock.
- [pyproject.toml](pyproject.toml) e `uv.lock`.

### Como correr

```bash
# a partir da raiz do repositório
./scripts/create-db.sh ex15 --pagila --reset
psql -d ex15 -c "CREATE MATERIALIZED VIEW monthly_revenue AS
  SELECT date_trunc('month', payment_date)::date AS month, sum(amount) AS revenue
  FROM payment GROUP BY 1;" -c "CREATE UNIQUE INDEX ON monthly_revenue (month);"
cd exercises/15-redis/exercise
uv sync
cp .env.example .env   # e trocar as passwords pelas do .env da raiz
uv run --env-file .env python demo.py
uv run --env-file .env python refresh.py & uv run --env-file .env python refresh.py & wait
```

O [.env.example](.env.example) já aponta `DATABASE_URL` para a base `ex15`; o `.env` está no `.gitignore`. O `--env-file` não substitui variáveis que já existam na shell; se tiveres feito `export DATABASE_URL=...` antes, faz `unset DATABASE_URL`. O `demo.py` demora até um minuto, porque a última parte espera pelo minuto seguinte.

### Output de `demo.py`

```
=== 1. Recently viewed films (sorted set) ===
customer 1 viewed films 1..25 in order
recent_views(1) -> [25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6]
  20 films, expected 25 down to 6: True
customer 1 viewed film 10 again
recent_views(1) -> [10, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 9, 8, 7, 6]
  film 10 first: True, appears once: True, size 20
TTL customer:1:viewed -> 2592000 s (30 days = 2592000)

=== 2. Cache-aside (film details) ===
setup: film 1 rental_rate = 0.99 in PostgreSQL, cache:film:1 deleted
get_film(1) -> MISS {'title': 'ACADEMY DINOSAUR', 'rating': 'PG', 'length': 86, 'rental_rate': Decimal('0.99')} | TTL 300 s
get_film(1) -> HIT  {'title': 'ACADEMY DINOSAUR', 'rating': 'PG', 'length': 86, 'rental_rate': Decimal('0.99')} | TTL 300 s
update_film_rate(1, 1.99) -> cache:film:1 exists: False
get_film(1) -> MISS {'title': 'ACADEMY DINOSAUR', 'rating': 'PG', 'length': 86, 'rental_rate': Decimal('1.99')} | TTL 300 s

=== 3. Lock (token + Lua release) ===
A acquire_lock -> token 6cd82982...
B acquire_lock -> None (held by A)
B release_lock with a wrong token -> False, lock still there: True
A release_lock with its token     -> True, lock still there: False
(two real processes: see refresh.py)

=== 4. Rate limit (10 per customer per minute) ===
12 calls -> [True, True, True, True, True, True, True, True, True, True, False, False]
  True: 10, False: 2
  ratelimit:1:29903921 = 12, TTL 120 s
waiting 44.9 s for the next minute...
next minute: allow_request(1) -> True (ratelimit:1:29903922 = 1)
```

### Output dos dois processos `refresh.py`

```
[14:42:00.376] pid 9820: acquired lock:refresh:monthly_revenue (token 516beb83...)
[14:42:00.376] pid 9819: skipped, lock lock:refresh:monthly_revenue is held (TTL 60 s)
[14:42:00.406] pid 9820: refreshed monthly_revenue (55 months), holding the lock 5 s
[14:42:05.411] pid 9820: released the lock
```

Os dois arrancam no mesmo milissegundo; o `SET ... NX` é atómico, por isso só um consegue a chave. O outro vê a chave existente e desiste sem fazer o refresh.

### Notas sobre cada padrão

**1. Vistos recentemente.** `ZADD` com o tempo atual como score: se o filme já está no conjunto, só o score muda, por isso voltar a ver o filme 10 passa-o para a frente sem duplicar. `ZREMRANGEBYRANK key 0 -21` apaga tudo menos os 20 scores mais altos, e `EXPIRE` renova os 30 dias a cada visualização. Os três comandos vão num pipeline `MULTI/EXEC`, por isso outro cliente nunca vê o conjunto com 21 elementos ou sem TTL.

**2. Cache-aside.** A aplicação lê primeiro o Redis; num miss lê o PostgreSQL e grava o JSON com `SET ... EX 300`. Na atualização escreve primeiro no PostgreSQL (commit) e só depois apaga a chave: se apagasse antes, uma leitura concorrente podia voltar a pôr na cache o valor antigo. Apagar em vez de reescrever a cache evita que duas atualizações concorrentes deixem na cache a versão errada. O `rental_rate` é guardado como string (`"0.99"`) para não perder precisão num `float`.

**3. Lock.** `SET lock NX EX 60` com um token aleatório (`secrets.token_hex(16)`). O `EX 60` garante que o lock desaparece se o processo morrer. A libertação é um script Lua que faz `GET` e `DEL` atomicamente e só apaga se o valor for o nosso token. Com um `GET` seguido de `DEL` no Python, o lock podia expirar entre os dois comandos, outro processo adquiri-lo, e nós apagaríamos o lock dele. O `demo.py` mostra que uma libertação com um token errado devolve `False` e deixa o lock intacto. O `REFRESH ... CONCURRENTLY` precisa do índice único em `month`.

**4. Rate limit.** Janela fixa: uma chave por cliente e por minuto (`int(time.time()) // 60`), `INCR` e `EXPIRE ... NX` no mesmo pipeline. O `INCR` é atómico, por isso pedidos concorrentes nunca passam do limite. O TTL é de 120 s (mais do que o minuto) para a chave não desaparecer antes de a janela acabar; quando o minuto muda, a chave muda, por isso o contador recomeça em 1. A desvantagem (até 20 pedidos em poucos segundos à volta da mudança de minuto) é o tema do challenge.

### Chaves usadas

| Padrão de chave | Tipo Redis | TTL | Para que serve |
| --- | --- | --- | --- |
| `customer:{customer_id}:viewed` | sorted set (membro = `film_id`, score = timestamp) | 30 dias (2,592,000 s), renovado a cada visualização | Os 20 filmes vistos mais recentemente pelo cliente |
| `cache:film:{film_id}` | string (JSON com `title`, `rating`, `length`, `rental_rate`) | 300 s | Cópia em cache dos detalhes do filme, apagada quando o `rental_rate` muda |
| `lock:refresh:monthly_revenue` | string (token aleatório) | 60 s | Lock para só um processo fazer o refresh da vista materializada |
| `lock:demo` | string (token aleatório) | 60 s | Lock usado no `demo.py` para mostrar a libertação com token errado |
| `ratelimit:{customer_id}:{minuto}` | string (contador `INCR`) | 120 s | Número de pedidos do cliente no minuto `{minuto}` (minutos desde a epoch) |
