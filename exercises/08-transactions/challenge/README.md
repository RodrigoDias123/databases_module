# Challenge 08: Transactions and concurrency

Opcional.

## Enunciado

Folder: `exercises/08-transactions/challenge/`

**Goal.** Build a job queue in PostgreSQL that processes each job exactly once with several workers.

**Starting point.** An empty database (`./scripts/create-db.sh ch08 --reset`) with these tables:

```sql
CREATE TABLE job (
    job_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payload jsonb NOT NULL,
    status  text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done'))
);

CREATE TABLE job_result (
    job_id       bigint NOT NULL REFERENCES job,
    worker       integer NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT now()
);
```

**Tasks.**

1. `producer.py` inserts 10,000 jobs with payload `{"n": <number>}`.
2. `worker.py` loops until there are no pending jobs. In one transaction it claims a job with `SELECT ... WHERE status = 'pending' ORDER BY job_id FOR UPDATE SKIP LOCKED LIMIT 1`, processes it (sleep 1 to 5 ms and insert a row into `job_result`), sets `status = 'done'` and commits.
3. Start 8 workers at the same time and prove that every job was processed exactly once: 10,000 rows in `job_result` and no `job_id` with more than one row.
4. Add one job whose processing sleeps 30 seconds. Kill the worker that takes it (`kill -9`) while it sleeps. Show what happens to the job, its row lock and its `job_result` row, and which worker processes it afterwards.

**Deliverables.**

- `producer.py`, `worker.py`, `pyproject.toml`.
- `README.md` with the commands, the queries that prove task 3, and the evidence and explanation of task 4, including what would change if processing sent an email instead of inserting a row.

**Done when.** Task 3 shows 10,000 results with no duplicates, and task 4 shows the killed job back in `pending` and later processed by another worker.

## Resolução

Ficheiros entregues:

- [schema.sql](schema.sql): as tabelas `job` e `job_result` do enunciado (começa com `DROP TABLE IF EXISTS`, para poder correr outra vez).
- [producer.py](producer.py): insere 10 000 jobs com payload `{"n": 1..10000}`. Com `--slow 30` insere antes um só job que demora 30 s (`{"n": 10001, "sleep": 30}`).
- [worker.py](worker.py): o worker. Recebe o número do worker como argumento.
- [observe.sql](observe.sql): as queries da tarefa 4 (estado do job, lock da linha, resultado, sessão que o tem).
- [pyproject.toml](pyproject.toml): dependência `psycopg[binary]`.

### Como correr

A partir da root do repositório:

```bash
./scripts/create-db.sh ch08 --reset
psql -d ch08 -v ON_ERROR_STOP=1 -f exercises/08-transactions/challenge/schema.sql
psql -d ch08 -c "CREATE EXTENSION pgrowlocks;"   # só para observar os locks na tarefa 4
```

Nesta pasta:

```bash
uv sync
uv run python producer.py
for i in 1 2 3 4 5 6 7 8; do uv run python worker.py $i & done; wait
```

Os scripts ligam-se com as variáveis do libpq (`PGHOST`, `PGUSER`, `PGPASSWORD`) já definidas no devcontainer, à base `ch08` (ou `PGDATABASE`).

### O worker

Cada job é uma transação:

```sql
BEGIN;
SELECT job_id, payload FROM job
WHERE status = 'pending'
ORDER BY job_id
FOR UPDATE SKIP LOCKED
LIMIT 1;
INSERT INTO job_result (job_id, worker) VALUES (<job_id>, <worker>);
-- sleep 1 a 5 ms (ou payload->'sleep' segundos)
UPDATE job SET status = 'done' WHERE job_id = <job_id>;
COMMIT;
```

- `FOR UPDATE` faz lock da linha do job até ao `COMMIT`. Nenhum outro worker pode reclamar o mesmo job enquanto este o tem.
- `SKIP LOCKED` faz com que os outros workers **saltem** as linhas bloqueadas em vez de esperarem por elas. Cada worker apanha o primeiro job `pending` que ninguém tem. Sem `SKIP LOCKED`, os 8 workers ficariam todos à espera do mesmo job e trabalhariam um de cada vez.
- O `INSERT` em `job_result` e o `UPDATE` do `status` estão na mesma transação que o lock. Ou ficam os dois, ou não fica nenhum.
- O loop termina quando o `SELECT` não devolve nada: não há jobs `pending` que não estejam bloqueados.

**Um erro que encontrei.** A primeira versão abria a ligação sem `autocommit` e corria `SELECT pg_backend_pid()` antes do loop. No psycopg isso abre uma transação implícita, e cada `with conn.transaction():` dentro dela passa a ser um `SAVEPOINT`, não um `BEGIN`/`COMMIT`. Cada worker ficava com **uma** transação aberta do início ao fim e só fazia commit ao fechar a ligação. O resultado da tarefa 3 até estava certo, mas por acaso:

- os locks de todos os jobs processados ficavam presos até ao fim;
- um crash a meio desfazia todo o trabalho desse worker;
- demorou 27 s em vez de 5 s, porque cada `SKIP LOCKED` tinha de saltar milhares de linhas bloqueadas.

O sinal estava no `pg_stat_activity`: o `backend_xid` (71989) era diferente do `xmax` da linha (71990), porque o lock era de uma subtransação. A correção foi `psycopg.connect(..., autocommit=True)`, para que cada `conn.transaction()` seja uma transação a sério.

### Tarefa 3: 8 workers, cada job processado exatamente uma vez

```
$ uv run python producer.py
Inserted 10000 jobs
$ time (for i in 1 2 3 4 5 6 7 8; do uv run python worker.py $i & done; wait)
worker 1: started, pid 17713, backend pid 3026
worker 3: started, pid 17714, backend pid 3027
worker 6: started, pid 17715, backend pid 3028
worker 4: started, pid 17718, backend pid 3029
worker 7: started, pid 17717, backend pid 3030
worker 2: started, pid 17716, backend pid 3031
worker 5: started, pid 17720, backend pid 3032
worker 8: started, pid 17719, backend pid 3033
worker 2: no pending jobs, processed 1232
worker 7: no pending jobs, processed 1258
worker 1: no pending jobs, processed 1265
worker 6: no pending jobs, processed 1249
worker 3: no pending jobs, processed 1250
worker 5: no pending jobs, processed 1245
worker 8: no pending jobs, processed 1250
worker 4: no pending jobs, processed 1251

real    0m5.234s
```

Provas:

```sql
-- 10 000 resultados, 10 000 jobs diferentes
SELECT count(*) AS results, count(DISTINCT job_id) AS distinct_jobs FROM job_result;
```
```
 results | distinct_jobs
---------+---------------
   10000 |         10000
```

```sql
-- nenhum job com mais de um resultado
SELECT job_id, count(*) FROM job_result GROUP BY job_id HAVING count(*) > 1;
```
```
 job_id | count
--------+-------
(0 rows)
```

```sql
-- todos os jobs ficaram done, e nenhum done ficou sem resultado
SELECT status, count(*) FROM job GROUP BY status;
SELECT count(*) AS done_without_result
FROM job j
WHERE status = 'done'
  AND NOT EXISTS (SELECT 1 FROM job_result r WHERE r.job_id = j.job_id);
```
```
 status | count
--------+-------
 done   | 10000

 done_without_result
---------------------
                   0
```

```sql
-- o trabalho foi repartido pelos 8 workers
SELECT worker, count(*) FROM job_result GROUP BY worker ORDER BY worker;
```
```
 worker | count
--------+-------
      1 |  1265
      2 |  1232
      3 |  1250
      4 |  1251
      5 |  1245
      6 |  1249
      7 |  1258
      8 |  1250
```

Os 8 totais somam 10 000, igual ao `processed` que cada worker escreveu ao terminar. Como 10 000 linhas = 10 000 `job_id` distintos, cada job foi processado **exatamente uma vez**.

### Tarefa 4: matar o worker a meio de um job

Sequência (com a fila da tarefa 3 já toda `done`):

```bash
uv run python producer.py --slow 30          # Inserted slow job 10001 (sleeps 30 s)
uv run python worker.py 1 &                   # apanha o job 10001 e dorme 30 s
psql -d ch08 -v job=10001 -f observe.sql      # (a) enquanto dorme
psql -d ch08 -c "SELECT job_id FROM job WHERE job_id = 10001 FOR UPDATE NOWAIT"
uv run python worker.py 2                     # outro worker ao mesmo tempo
kill -9 <pid do worker 1>
psql -d ch08 -v job=10001 -f observe.sql      # (b) depois do kill
uv run python worker.py 3                     # (c) outro worker
```

#### (a) Enquanto o worker 1 dorme

```
worker 1: started, pid 17831, backend pid 3061
worker 1: job 10001 sleeps 30 s
```

```
 job_id |          payload          | status  | xmax
--------+---------------------------+---------+-------
  10001 | {"n": 10001, "sleep": 30} | pending | 82002

 locked_row | locker | multi |     modes      |  pids
------------+--------+-------+----------------+--------
 (101,50)   |  82002 | f     | {"For Update"} | {3061}

 results_for_job
-----------------
               0

 pid  |        state        | backend_xid | in_transaction_for |                          query
------+---------------------+-------------+--------------------+---------------------------------------------------------
 3061 | idle in transaction |       82002 | 00:00:02.153574    | INSERT INTO job_result (job_id, worker) VALUES ($1, $2)

 n_tup_ins | n_live_tup | n_dead_tup
-----------+------------+------------
     10000 |      10000 |          0
```

- **Job:** continua `pending` para quem olha de fora. O `UPDATE ... 'done'` ainda não foi feito, e mesmo que fosse, não se veria antes do commit.
- **Lock:** `pgrowlocks` mostra a linha do job com lock `For Update`, da transação 82002, do backend 3061, que é o do worker 1. O `xmax` da linha é esse mesmo id de transação. É assim que o Postgres marca um lock de linha.
- **`job_result`:** o worker 1 já fez o `INSERT`, mas outras sessões não o veem (0 linhas), porque ainda não houve commit.
- **Sessão:** `idle in transaction`: o backend tem uma transação aberta e está à espera do cliente, que está no `sleep`.

Outra sessão que tente o lock com `NOWAIT` falha logo:

```
ERROR:  could not obtain lock on row in relation "job"
```

E um worker que arranca ao mesmo tempo salta o job bloqueado (`SKIP LOCKED`). Não encontra mais nada e termina sem processar nenhum job:

```
worker 2: started, pid 17857, backend pid 3065
worker 2: no pending jobs, processed 0
```

#### (b) Depois do `kill -9`

```
$ kill -9 17831
/bin/bash: line 28: 17831 Killed    $PY worker.py 1
```

Log do servidor (`docker compose logs postgres`):

```
2026-10-30 20:53:06.999 UTC [3061] LOG:  unexpected EOF on client connection with an open transaction
```

```
 job_id |          payload          | status  | xmax
--------+---------------------------+---------+-------
  10001 | {"n": 10001, "sleep": 30} | pending | 82002

 locked_row | locker | multi | modes | pids
------------+--------+-------+-------+------
(0 rows)

 results_for_job
-----------------
               0

 pid | state | backend_xid | in_transaction_for | query
-----+-------+-------------+--------------------+-------
(0 rows)

 n_tup_ins | n_live_tup | n_dead_tup
-----------+------------+------------
     10001 |      10000 |          1
```

- **Sessão:** o processo Python morreu sem fechar nada, mas o sistema operativo fechou a socket TCP. O backend 3061 recebeu EOF ("unexpected EOF ... with an open transaction"), fez **rollback** da transação e terminou. Já não aparece no `pg_stat_activity`.
- **Lock:** `pgrowlocks` não mostra nada: o lock da linha foi libertado com o rollback. O `xmax` continua a ser 82002, mas é de uma transação abortada, por isso o Postgres ignora-o.
- **Job:** continua `pending`. Como o `UPDATE` nunca teve commit, o job volta a estar disponível para qualquer worker.
- **`job_result`:** a linha inserida pelo worker 1 nunca teve commit. Não ficou nenhum resultado para o job 10001. As estatísticas mostram que ela existiu: `n_tup_ins` passou a 10 001, mas é um tuplo morto (`n_dead_tup = 1`) que o `VACUUM` vai limpar.

#### (c) Outro worker processa o job

```
$ time uv run python worker.py 3
worker 3: started, pid 17900, backend pid 3067
worker 3: job 10001 sleeps 30 s
worker 3: no pending jobs, processed 1

real    0m30.142s
```

```
 job_id | status | worker |         processed_at
--------+--------+--------+-------------------------------
  10001 | done   |      3 |  2026-10-30 20:53:08.685226+00

 results | distinct_jobs
---------+---------------
   10001 |         10001
```

O job 10001 foi processado pelo **worker 3**, ficou `done` e tem **uma** linha em `job_result`. A fila continua com exatamente um resultado por job. (O `processed_at` é o `now()` do início da transação, e por isso marca o momento em que o worker 3 apanhou o job, não o fim dos 30 s.)

**Porque funciona.** A posse do job ("está a ser processado por alguém") não está numa coluna (`status = 'processing'`). Está no lock da linha, e esse lock só existe enquanto a transação do worker existir. Se o worker morrer, a ligação cai, a transação é desfeita e o lock desaparece. Não é preciso nenhum processo de limpeza nem timeout para "recuperar" jobs presos. Se fosse uma coluna `processing` com commit, um worker morto deixava o job preso para sempre.

O mesmo mecanismo tem dois limites:

- Um worker que **não morre mas fica preso** (por exemplo, à espera de uma chamada de rede que não responde) mantém o lock para sempre. Em produção configura-se `idle_in_transaction_session_timeout` (ou um timeout no próprio processamento) para o Postgres cortar a sessão.
- Um job longo mantém uma transação aberta durante todo o processamento. Transações longas impedem o `VACUUM` de limpar tuplos mortos. Isto serve para jobs de milissegundos ou segundos, não de horas.

### E se o processamento enviasse um email?

O `INSERT` em `job_result` é seguro porque está **dentro** da transação: quando o worker 1 morreu, o rollback desfez-o, e o worker 3 inseriu a única linha que ficou. Um email não está na base de dados. Não há rollback que "desenvie" um email.

Com o mesmo cenário:

1. O worker 1 apanha o job e envia o email. O email sai.
2. O worker 1 morre antes do `COMMIT`. O Postgres faz rollback: o job volta a `pending`.
3. O worker 3 apanha o job e **envia o email outra vez**.

O cliente recebe **dois emails**. A fila garante que cada job tem exatamente um *commit*, mas o efeito externo passa a ser **pelo menos uma vez** (*at-least-once*), não exatamente uma vez. Se o envio for feito depois do commit, o problema inverte-se: o worker pode morrer entre o commit e o envio, e o email nunca sai (*at-most-once*).

Como lidar com isso:

- **Idempotência no destino.** Enviar com uma chave única (por exemplo, `job_id`) que o serviço de email use para ignorar duplicados. Muitos fornecedores aceitam um *idempotency key*. É a única forma de chegar perto de "exatamente uma vez" num efeito externo.
- **Registar o envio na base de dados.** Numa transação, marcar o job como `sending` e fazer commit. Enviar. Noutra transação, marcar como `sent`. Se o worker morrer entre as duas, o job fica em `sending`, e alguém (uma pessoa ou um processo) decide se reenvia, em vez de reenviar sem saber.
- **Tornar o reenvio aceitável.** Para muitos emails (notificações, por exemplo), um duplicado ocasional é tolerável, e *at-least-once* com retries é o que se escolhe.
