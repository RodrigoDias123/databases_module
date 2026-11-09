# Challenge 16: Redis II, source of truth, rebuild and persistence

Opcional.

## Enunciado

Folder: `exercises/16-consistency/challenge/`

**Goal.** Keep Redis in sync with PostgreSQL without a full rebuild, even when the worker or Redis fails, using the transactional outbox pattern.

**Starting point.** The `ex16` database, the sets built by `rebuild.py` and the `verify.py` of the exercise above. Turn on AOF with `docker-compose.redis-aof.yml` (following the warning in `sessions/16-redis-consistency/`), then run `CONFIG SET appendfsync always` in `redis-cli`. In this challenge, always restart Redis with the same `-f` files and run that `CONFIG SET` again after each restart, before the worker writes. Add this table to `ex16`:

```sql
CREATE TABLE outbox (
    outbox_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id  integer NOT NULL,
    film_id      integer NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz
);
```

**Tasks.**

1. `rent.py` inserts N new rentals (the number is an argument) for random existing customers and copies. Each rental and its `outbox` row are inserted in the same PostgreSQL transaction.
2. `worker.py` loops: in one transaction it claims up to 50 unprocessed rows with `FOR UPDATE SKIP LOCKED`, adds the categories of each film to `customer:{customer_id}:categories`, sets `processed_at` and commits.
3. Run `rent.py 5000` while the worker runs. Kill the worker (`kill -9`) in the middle of a batch and start it again. Then stop Redis (`docker compose kill redis`) in the middle of a batch, start it again with AOF on and let the worker finish.
4. Run `verify.py` at the end.
5. Explain why processing the same outbox row twice is harmless here, and what you would need if it were not (for example an `INCR`). Explain also why the result depends on Redis persistence: what could be lost with RDB only, or with `appendfsync everysec`, and why the outbox alone would not bring it back.

**Deliverables.**

- `rent.py`, `worker.py`.
- `README.md` with the steps you ran, the worker log around both failures, the final output of `verify.py`, and the explanation of task 5.

**Done when.** After both failures, every outbox row is processed and `verify.py` exits with 0 without running `rebuild.py`.

## Resolução

Ficheiros entregues:

- [rent.py](rent.py): insere N alugueres, cada um com a sua linha na `outbox`, na mesma transação.
- [worker.py](worker.py): processa a `outbox` em lotes de 50 com `FOR UPDATE SKIP LOCKED`.
- [outbox.sql](outbox.sql): a tabela do enunciado, mais um índice parcial nas linhas por processar.
- [failures.sh](failures.sh): o script que corre a tarefa 3 (os alugueres, as duas falhas e os reinícios) e guarda os logs em `logs/` (fora do git).
- [pyproject.toml](pyproject.toml) e `uv.lock`; [.env.example](.env.example) igual ao do exercício (`ex16`, Redis base 1).
- O `verify.py` é o do exercício: `../exercise/verify.py`.

### Passos

```bash
# a partir da raiz do repositório
./scripts/create-db.sh ex16 --pagila --reset
export REDISCLI_AUTH="$REDIS_PASSWORD"

# AOF, seguindo o aviso da sessão 16: primeiro CONFIG SET (o Redis escreve as chaves
# atuais num AOF novo), só depois recriar o contentor com o ficheiro do AOF.
# Sem o primeiro passo o Redis arrancava vazio e todos os projetos perdiam as chaves.
redis-cli -h redis CONFIG SET appendonly yes
redis-cli -h redis INFO persistence | grep aof_rewrite_in_progress   # esperar por 0
docker compose -f docker-compose.yml -f docker-compose.redis-aof.yml up -d --wait redis
redis-cli -h redis CONFIG SET appendfsync always

cd exercises/16-consistency/challenge
uv sync
cp .env.example .env            # e trocar as passwords pelas do .env da raiz
unset REDIS_URL DATABASE_URL    # o devcontainer exporta REDIS_URL para a base 0
redis-cli -h redis -n 1 FLUSHDB
psql -d ex16 -f outbox.sql
uv run --env-file .env python ../exercise/rebuild.py    # checked: 997 sets, OK
uv run --env-file .env python ../exercise/verify.py

./failures.sh                   # tarefa 3
uv run --env-file .env python ../exercise/verify.py     # tarefa 4
```

O `failures.sh` faz, por esta ordem:

1. arranca `worker.py --pause 0.3` e, um segundo depois, `rent.py 5000 --delay 0.002`. O `--pause` deixa 0,3 s entre a escrita no Redis e o `COMMIT`, para a falha cair a meio de um lote;
2. quando a última linha do log é `redis updated` (escrita no Redis feita, `COMMIT` por fazer), faz `kill -9` ao processo Python do worker e arranca outro;
3. quando a última linha é `claimed`, faz `docker compose kill redis` (SIGKILL, como num crash), espera 3 s e arranca o Redis com os mesmos `-f`. Não usa `--wait`, que fica à espera do healthcheck (5 s): repete o `CONFIG SET appendfsync always` até o Redis responder, para correr antes de o worker voltar a escrever;
4. o segundo worker termina quando passa 5 s sem nada para fazer (`--exit-when-idle 5`).

### `rent.py`

Para cada aluguer escolhe um cliente e uma cópia (`inventory`) ao acaso, e um funcionário da loja da cópia. Dentro de `with conn.transaction()` faz o `INSERT INTO rental` e o `INSERT INTO outbox (customer_id, film_id)`: ou ficam os dois gravados ou nenhum. Se o processo morrer entre os dois, a transação é desfeita e não fica um aluguer sem linha na `outbox`, nem uma linha na `outbox` para um aluguer que não existe. Escrever diretamente no Redis a partir do `rent.py` teria exatamente esse problema: o `COMMIT` e o `SADD` são dois sistemas sem transação comum.

### `worker.py`

Cada lote é uma transação PostgreSQL:

1. `SELECT ... WHERE processed_at IS NULL ORDER BY outbox_id LIMIT 50 FOR UPDATE SKIP LOCKED`: bloqueia até 50 linhas; outro worker salta essas linhas em vez de ficar à espera, por isso podem correr vários workers em paralelo;
2. uma query com as categorias de todos os filmes do lote, e um pipeline com um `SADD customer:{id}:categories ...` por linha;
3. `UPDATE outbox SET processed_at = now()` e `COMMIT`.

Se o worker morrer ou o Redis falhar antes do `COMMIT`, a transação é desfeita (o PostgreSQL faz o rollback quando a ligação cai), os locks são libertados e as linhas voltam a estar por processar. Um erro do Redis é apanhado: o worker regista-o, espera (0,5 s, 1 s, 2 s, até 5 s) e tenta outra vez. A garantia é *at least once*: cada linha chega ao Redis pelo menos uma vez, às vezes duas.

### Log do worker à volta das duas falhas

Execução de 5000 alugueres ([failures.sh](failures.sh)). As linhas `>>>` são do script.

**`kill -9` ao worker** entre a escrita no Redis e o `COMMIT` do lote 562..611:

```
[15:04:56.687] worker 23532: committed 512..561
[15:04:56.688] worker 23532: claimed 50 rows 562..611
[15:04:56.692] worker 23532: redis updated for 562..611
[15:04:56.875] >>> kill -9 23532 (worker)
[15:04:57.889] >>> worker started again
[15:04:58.036] worker 23593: started
[15:04:58.037] worker 23593: claimed 50 rows 562..611
[15:04:58.039] worker 23593: redis updated for 562..611
[15:04:58.342] worker 23593: committed 562..611
[15:04:58.343] worker 23593: claimed 50 rows 612..661
```

O lote 562..611 já estava no Redis mas não tinha `COMMIT`. O PostgreSQL desfez a transação, e o novo worker voltou a reclamar exatamente as mesmas linhas e repetiu os `SADD`.

**`docker compose kill redis`** a meio do lote 2912..2961:

```
[15:05:12.449] worker 23593: committed 2862..2911
[15:05:12.450] worker 23593: claimed 50 rows 2912..2961
[15:05:12.452] >>> docker compose kill redis
[15:05:12.454] worker 23593: redis updated for 2912..2961
[15:05:12.755] worker 23593: committed 2912..2961
[15:05:12.756] worker 23593: claimed 50 rows 2962..3011
[15:05:12.761] worker 23593: redis error, batch rolled back: ConnectionError: Error -2 connecting to redis:6379. Name or service not known.; retry in 0.5 s
[15:05:13.269] worker 23593: claimed 50 rows 2962..3011
[15:05:13.278] worker 23593: redis error, batch rolled back: ConnectionError: Error -2 connecting to redis:6379. Name or service not known.; retry in 1.0 s
[15:05:14.284] worker 23593: claimed 50 rows 2962..3011
[15:05:14.294] worker 23593: redis error, batch rolled back: ConnectionError: Error -2 connecting to redis:6379. Name or service not known.; retry in 2.0 s
[15:05:15.644] >>> redis starting again (AOF files)
[15:05:15.824] >>> redis up, CONFIG SET appendfsync always
[15:05:16.298] worker 23593: claimed 50 rows 2962..3011
[15:05:16.306] worker 23593: redis updated for 2962..3011
...
[15:05:29.006] worker 23593: committed 4962..5000
[15:05:34.090] worker 23593: idle for 5.0 s, 0 unprocessed rows left, exiting
```

O `docker compose kill` demora alguns milissegundos a chegar ao contentor, por isso o lote 2912..2961 ainda foi escrito no Redis e confirmado, e só depois o PostgreSQL fez o `COMMIT`. É o caso perigoso: a `outbox` diz que o lote está processado, e o Redis morreu logo a seguir. Só a persistência do Redis o salva (ver tarefa 5). O lote seguinte, 2962..3011, falhou três vezes enquanto o Redis estava em baixo, foi desfeito de cada vez e passou à quarta tentativa. O `CONFIG SET` (15.824) correu antes de o worker voltar a escrever (16.298).

### Resultado final (tarefa 4)

```
$ psql -d ex16 -c "SELECT count(*) AS total, count(processed_at) AS processed,
                   count(*) FILTER (WHERE processed_at IS NULL) AS unprocessed FROM outbox"
 total | processed | unprocessed
-------+-----------+-------------
  5000 |      5000 |           0

$ uv run --env-file .env python ../exercise/verify.py
checked 999 sets, 999 keys in Redis: OK
exit code: 0
```

Sem correr o `rebuild.py`. Agora são 999 sets e não 997: os clientes 647 e 978 receberam alugueres novos, e o worker criou os sets deles.

### Tarefa 5: idempotência e persistência

**Processar a mesma linha duas vezes não faz mal.** O worker só faz `SADD` de nomes de categorias a um set, e um set não tem duplicados: `SADD customer:1:categories Action` deixa o set igual seja corrido uma vez ou dez. O resultado também não depende da ordem (aplicar 562..611 antes ou depois de 612..661 dá o mesmo set). Por isso a garantia *at least once* da outbox chega: a repetição depois do `kill -9` não se nota no resultado.

**Se não fosse idempotente** (por exemplo `INCR customer:{id}:rentals`), a repetição contava o mesmo aluguer duas vezes. Seria preciso tornar a aplicação idempotente, registando no próprio Redis que linhas já foram aplicadas, de forma atómica com a escrita:

- um script Lua (ou `MULTI/EXEC`) que faz `SADD outbox:applied {outbox_id}` e só faz o `INCR` se o `SADD` devolver 1. O registo e o efeito entram juntos, por isso uma repetição é ignorada. O conjunto `outbox:applied` cresce, e só se pode limpar depois do `COMMIT` no PostgreSQL;
- ou guardar por chave o último `outbox_id` aplicado (`HSET ... last_id`) e ignorar IDs menores, se as linhas de cada chave forem processadas por ordem.

**Porque é que o resultado depende da persistência do Redis.** O worker marca a linha como processada (`COMMIT`) *depois* de o Redis confirmar o `SADD`. A partir daí, a outbox não volta a enviá-la. Se o Redis perder essa escrita depois de a confirmar, ninguém a repõe:

- **Só RDB** (`save 3600 1 300 100 60 10000`): ao reiniciar, o Redis carrega o último snapshot. Tudo o que foi escrito depois perde-se: com o volume desta corrida, minutos de lotes, ou mesmo uma hora numa altura calma. As linhas desses lotes estão todas com `processed_at` preenchido, e o `verify.py` falharia (como na demo de RDB da sessão 16, em que 100 % das escritas desde o snapshot desapareceram).
- **AOF com `appendfsync everysec`**: o Redis passa cada escrita ao sistema operativo antes de responder, mas só faz `fsync` uma vez por segundo. Um SIGKILL ao processo não perde nada (o kernel ainda escreve o ficheiro); uma falha de energia ou do kernel pode perder até cerca de 1 s de escritas já confirmadas, e portanto lotes já com `COMMIT`.
- **AOF com `appendfsync always`** (o que o enunciado pede): o `fsync` é feito antes de o Redis responder, por isso uma escrita confirmada já está no disco quando o worker faz o `COMMIT`.

**A outbox sozinha não chega** porque só garante uma coisa: cada linha é aplicada até o Redis a confirmar. Depois do `COMMIT` a linha está marcada como processada e o worker nunca mais olha para ela. O PostgreSQL não sabe que o Redis perdeu a escrita, e o worker também não. Para recuperar seria preciso voltar a aplicar linhas já processadas (por exemplo, todas as dos últimos minutos, já que o `SADD` é idempotente) ou correr o `rebuild.py` a partir do PostgreSQL. A outbox mantém o Redis em dia; não substitui a durabilidade do Redis nem o rebuild.

### Voltar à configuração normal

As outras sessões esperam o Redis sem AOF. A partir da raiz:

```bash
docker compose up -d --wait redis
```

O Redis grava um snapshot ao parar e o contentor novo carrega-o, por isso as chaves mantêm-se.
