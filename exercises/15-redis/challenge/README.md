# Challenge 15: Redis I, data structures and patterns

Opcional.

## Enunciado

Folder: `exercises/15-redis/challenge/`

**Goal.** Replace the fixed-window rate limit with a sliding window and prove the difference with a test.

**Starting point.** The `allow_request` function of the exercise above, and `uv add pytest`.

**Tasks.**

1. Change the fixed-window function so that it takes the current time as an argument, `allow_request_fixed(customer_id, now)`, so that tests control the clock.
2. Write `allow_request_sliding(customer_id, now)`: 10 requests in any 60-second window, stored in a sorted set with the request time as score. Implement it as a Lua script that removes old entries, counts, and adds the new request in one atomic step. Each member must be unique even when two requests have the same time.
3. Write a pytest test that sends 10 requests at seconds 59.0 to 59.9 of one minute and 10 more at seconds 0.0 to 0.9 of the next, and shows that the fixed window accepts all 20 while the sliding window accepts only 10.
4. Write a test that sends 30 requests from 10 threads at the same moment to the sliding window and checks that exactly 10 are accepted.

**Deliverables.**

- The rate limit module and `tests/test_rate_limit.py`.
- `README.md` with `uv run pytest -v` output and an explanation of why the check and the insert must be atomic.

**Done when.** Both tests pass and show 20 accepted by the fixed window, 10 by the sliding window, and exactly 10 under concurrency.

## Resolução

Ficheiros entregues:

- [rate_limit.py](rate_limit.py): `allow_request_fixed(customer_id, now)` e `allow_request_sliding(customer_id, now)` (script Lua).
- [tests/test_rate_limit.py](tests/test_rate_limit.py): os testes das tarefas 3 e 4, mais um teste que mostra a janela deslizante a libertar lugar ao fim de 60 s.
- [pyproject.toml](pyproject.toml) e `uv.lock`; [.env.example](.env.example) com o `REDIS_URL`.

### Como correr

```bash
cd exercises/15-redis/challenge
uv sync
cp .env.example .env   # e trocar a password pela do .env da raiz
uv run --env-file .env pytest -v
```

Os testes usam o cliente `900001` (fora do Pagila) e apagam as chaves dele antes e depois de cada teste. O relógio é passado como argumento (`now`), por isso os testes não esperam por minuto nenhum e correm em menos de um segundo.

### Tarefas 1 e 2: as duas funções

**Janela fixa.** É o `allow_request` do exercício, mas a janela vem de `now` em vez de `time.time()`: a chave é `ratelimit:fixed:{customer_id}:{int(now // 60)}`, com `INCR` e `EXPIRE ... NX` de 120 s. O contador recomeça sempre no segundo 0 de cada minuto.

**Janela deslizante.** Uma sorted set por cliente, `ratelimit:sliding:{customer_id}`, com um membro por pedido aceite e o tempo do pedido como score. O script Lua faz, num só passo:

1. `ZREMRANGEBYSCORE key -inf now-60` apaga os pedidos com 60 s ou mais, ficando a janela `(now-60, now]`;
2. `ZCARD key` conta os pedidos que ficaram;
3. se forem menos de 10, `ZADD key now membro` e `PEXPIRE` de 60 s (a chave desaparece se o cliente ficar um minuto parado), e devolve 1; senão devolve 0.

Os pedidos rejeitados não são guardados, por isso um cliente que insiste não fica bloqueado para sempre.

**Membros únicos.** Numa sorted set o membro é a identidade: dois `ZADD` com o mesmo membro dão um só elemento. Se o membro fosse só o tempo, dois pedidos no mesmo instante contavam como um e o limite deixava passar mais de 10. O membro é `"{now}:{uuid4}"`, único mesmo com o mesmo score. O teste de concorrência confirma: 30 pedidos com o mesmo `now` deixam exatamente 10 membros.

### Output de `uv run pytest -v`

```
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.2.0, pluggy-1.7.0 -- /workspaces/databases_module/exercises/15-redis/challenge/.venv/bin/python
cachedir: .pytest_cache
rootdir: /workspaces/databases_module/exercises/15-redis/challenge
configfile: pyproject.toml
testpaths: tests
collecting ... collected 3 items

tests/test_rate_limit.py::test_fixed_window_accepts_20_sliding_accepts_10_at_minute_boundary PASSED [ 33%]
tests/test_rate_limit.py::test_sliding_window_accepts_again_after_60_seconds PASSED [ 66%]
tests/test_rate_limit.py::test_sliding_window_exactly_10_of_30_concurrent_requests PASSED [100%]

============================== 3 passed in 0.28s ===============================
```

Com `-s` os testes também mostram o que cada janela aceitou:

```
fixed:   20 accepted -> [True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True]
sliding: 10 accepted -> [True, True, True, True, True, True, True, True, True, True, False, False, False, False, False, False, False, False, False, False]
30 requests, 10 accepted, 20 rejected
```

**Fronteira do minuto.** Os 10 pedidos de 59.0 a 59.9 enchem o contador do minuto N. Às 0.0 do minuto N+1 a chave é outra e o contador recomeça, por isso a janela fixa aceita os 20 pedidos em 1,9 s, o dobro do limite. A janela deslizante às 0.0 ainda vê os 10 pedidos de há menos de 60 s e rejeita os 10 seguintes.

### Porque é que a verificação e a inserção têm de ser atómicas

A janela deslizante é um "ler, decidir, escrever": contar os pedidos da janela e, se houver lugar, inserir o novo. Se forem comandos separados, vários clientes podem ler a mesma contagem antes de qualquer um escrever:

```
thread A: ZCARD -> 9     (há lugar)
thread B: ZCARD -> 9     (há lugar)
thread A: ZADD           -> 10 pedidos
thread B: ZADD           -> 11 pedidos, acima do limite
```

Para o confirmar, corri a mesma carga do teste 4 (10 threads, 30 pedidos no mesmo instante) contra uma versão com `ZREMRANGEBYSCORE`, `ZCARD` e `ZADD` como comandos separados do Python. Em 5 execuções foram aceites 13, 12, 14, 11 e 12 pedidos, nunca os 10 corretos.

O Redis executa cada script Lua de uma vez, sem intercalar comandos de outros clientes, por isso entre o `ZCARD` e o `ZADD` ninguém consegue inserir nada e a contagem que decide é sempre a atual. Um pipeline `MULTI/EXEC` não chegava: os comandos de uma transação só correm no `EXEC`, por isso não se pode usar o resultado do `ZCARD` para decidir se se faz o `ZADD`. Seria preciso `WATCH` com retries, o que dá mais idas ao servidor e muitas repetições quando há concorrência.

A janela fixa não tem este problema porque o `INCR` já é um "ler e escrever" atómico: cada pedido recebe um número diferente e só os 10 primeiros ficam `<= 10`.
