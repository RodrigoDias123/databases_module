# Exercício 08: Transactions and concurrency

## Enunciado

Folder: `exercises/08-transactions/exercise/`

**Goal.** Reproduce lost updates, deadlocks and write skew, and fix each one.

**Starting point.** A fresh copy of Pagila and a uv project:

```bash
./scripts/create-db.sh ex08 --pagila --reset
uv init --bare
uv add "psycopg[binary]"
```

Run this once in `ex08`. It adds a balance to every customer and brings store 1 from 6 to 20 active staff members:

```sql
ALTER TABLE customer ADD COLUMN balance numeric(10,2) NOT NULL DEFAULT 100 CHECK (balance >= 0);

INSERT INTO staff (first_name, last_name, address_id, store_id, username)
SELECT 'Temp', 'Staff ' || g, 1, 1, 'temp' || g
FROM generate_series(1, 14) AS g;
```

**Tasks.**

1. Lost update. In two `psql` sessions, each session withdraws 10 from customer 1 by reading the balance with `SELECT` and then writing the new value with `UPDATE ... SET balance = <value read - 10>`. Interleave the steps as in the tutorial so that the final balance is 90 instead of 80. Reset the balance to 100 afterwards.
2. Fix the lost update in two ways, repeating the same interleaving each time: an atomic `UPDATE ... SET balance = balance - 10 WHERE ... AND balance >= 10`, and `SELECT ... FOR UPDATE` before the update. Show that the final balance is 80 with both fixes.
3. Deadlock. In two sessions, session A updates customer 1 and then customer 2, and session B updates customer 2 and then customer 1, interleaved so that each waits for the other. Copy the full `ERROR: deadlock detected` message and explain each of its lines. Explain how to prevent it.
4. Write skew. The rule: every store keeps at least one active staff member. Write `write_skew.py`, which starts 20 threads, one per active staff member of store 1, each with its own connection. Each thread runs one transaction: count the active staff of store 1; if the count is above 1, set its own member to `active = false`; commit. Use a `threading.Barrier(20)` between the count and the update so that every thread reads before any thread writes.
   1. Run it under `READ COMMITTED` and show the number of active members of store 1 afterwards.
   2. Reset with `UPDATE staff SET active = true WHERE store_id = 1;`.
   3. Run it under `SERIALIZABLE`, retrying a transaction that fails with a serialisation error (SQLSTATE `40001`) from the start, without the barrier on retries. Show that exactly one member stays active.

**Deliverables.**

- `lost_update.md` and `deadlock.md` with the commands of each session in order (as a two-column table, like the tutorial) and the results.
- `write_skew.py`, `pyproject.toml`.
- `README.md` with the output of both runs of task 4 and an explanation of why `READ COMMITTED` breaks the rule and `SERIALIZABLE` does not.

**Done when.** The lost update and the deadlock are reproduced and explained, both fixes give a final balance of 80, the `READ COMMITTED` run leaves fewer than 1 active member, and the `SERIALIZABLE` run leaves exactly 1.

## Challenge (opcional, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [x] `lost_update.md`: lost update reproduced in two psql sessions (final balance 90)
- [x] Fix 1: atomic `UPDATE` (final balance 80)
- [x] Fix 2: `SELECT ... FOR UPDATE` (final balance 80)
- [x] `deadlock.md`: deadlock reproduced, message explained line by line, prevention
- [x] `write_skew.py`: rule broken under `READ COMMITTED`, exactly 1 active under `SERIALIZABLE` + retries
- [x] `README.md` with the output of both runs and the explanation

## Resolução

Ficheiros entregues:

- [lost_update.md](lost_update.md): tarefas 1 e 2 (lost update com saldo final 90, e as duas correções com saldo final 80).
- [deadlock.md](deadlock.md): tarefa 3 (deadlock, mensagem explicada linha a linha, prevenção).
- [write_skew.py](write_skew.py) e [pyproject.toml](pyproject.toml): tarefa 4.

### Como correr

A partir da root do repositório:

```bash
./scripts/create-db.sh ex08 --pagila --reset
psql -d ex08 -v ON_ERROR_STOP=1 <<'SQL'
ALTER TABLE customer ADD COLUMN balance numeric(10,2) NOT NULL DEFAULT 100 CHECK (balance >= 0);

INSERT INTO staff (first_name, last_name, address_id, store_id, username)
SELECT 'Temp', 'Staff ' || g, 1, 1, 'temp' || g
FROM generate_series(1, 14) AS g;
SQL
```

As tarefas 1 a 3 usam duas sessões `psql -d ex08`, com as instruções pela ordem das tabelas em `lost_update.md` e `deadlock.md`. Os resultados nessas tabelas são os que o PostgreSQL 18.6 devolveu.

Tarefa 4, nesta pasta:

```bash
uv sync
uv run python write_skew.py read-committed
psql -d ex08 -c "UPDATE staff SET active = true WHERE store_id = 1;"
uv run python write_skew.py serializable
```

O script liga-se com as variáveis do libpq (`PGHOST`, `PGUSER`, `PGPASSWORD`) já definidas no devcontainer, à base `ex08` (ou `PGDATABASE`). Recusa correr se a loja 1 não tiver exatamente 20 membros ativos, para lembrar o reset.

### Tarefa 4: write skew

Cada uma das 20 threads tem a sua ligação e corre uma transação:

1. `SELECT count(*) FROM staff WHERE store_id = 1 AND active`
2. `barrier.wait()` (`threading.Barrier(20)`, só na primeira tentativa)
3. se a contagem for maior que 1: `UPDATE staff SET active = false WHERE staff_id = <o seu>`
4. commit

Em `SERIALIZABLE`, uma transação que falha com `SerializationFailure` (SQLSTATE `40001`) é repetida desde o passo 1, sem a barreira.

#### Execução 1: `READ COMMITTED`

```
Isolation level: READ_COMMITTED, 20 threads, 20 active before
staff 1511  attempt 1  saw 20 active  -> deactivated
staff 1507  attempt 1  saw 20 active  -> deactivated
staff  36  attempt 1  saw 20 active  -> deactivated
staff 1421  attempt 1  saw 20 active  -> deactivated
staff 1505  attempt 1  saw 20 active  -> deactivated
staff 1512  attempt 1  saw 20 active  -> deactivated
staff 1514  attempt 1  saw 20 active  -> deactivated
staff   6  attempt 1  saw 20 active  -> deactivated
staff 1502  attempt 1  saw 20 active  -> deactivated
staff 1471  attempt 1  saw 20 active  -> deactivated
staff  27  attempt 1  saw 20 active  -> deactivated
staff 1503  attempt 1  saw 20 active  -> deactivated
staff 1513  attempt 1  saw 20 active  -> deactivated
staff 1509  attempt 1  saw 20 active  -> deactivated
staff 1436  attempt 1  saw 20 active  -> deactivated
staff 1506  attempt 1  saw 20 active  -> deactivated
staff 1508  attempt 1  saw 20 active  -> deactivated
staff 1510  attempt 1  saw 20 active  -> deactivated
staff 1504  attempt 1  saw 20 active  -> deactivated
staff 1501  attempt 1  saw 20 active  -> deactivated
Deactivated: 20, retries: 0
Active staff in store 1 afterwards: 0
RULE BROKEN
```

```
ex08=# SELECT count(*) AS active FROM staff WHERE store_id = 1 AND active;
 active
--------
      0
```

**0 membros ativos**: a regra foi violada.

Reset: `UPDATE staff SET active = true WHERE store_id = 1;` → `UPDATE 20`.

#### Execução 2: `SERIALIZABLE` com retries

Início e fim do output (79 retries no total). O output completo está abaixo.

```
Isolation level: SERIALIZABLE, 20 threads, 20 active before
staff 1513  attempt 1  saw 20 active  -> deactivated
staff 1505  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1507  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
...
staff 1502  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
...
staff   6  attempt 2  saw 19 active  -> deactivated
...
staff 1508  attempt 7  saw  3 active  -> deactivated
staff 1471  attempt 7  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1436  attempt 11  saw  2 active  -> deactivated
staff 1471  attempt 8  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1471  attempt 9  saw  1 active  -> stayed active
Deactivated: 19, retries: 79
Active staff in store 1 afterwards: 1
OK: rule kept
```

```
ex08=# SELECT staff_id, first_name, last_name FROM staff WHERE store_id = 1 AND active;
 staff_id | first_name | last_name
----------+------------+-----------
     1471 | Dan        | Kling
```

**Exatamente 1 membro ativo**: a regra foi cumprida.

<details>
<summary>Output completo da execução em <code>SERIALIZABLE</code></summary>

```
Isolation level: SERIALIZABLE, 20 threads, 20 active before
staff 1513  attempt 1  saw 20 active  -> deactivated
staff 1505  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1507  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1508  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1436  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff   6  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1514  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1471  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1502  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1511  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff  27  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1501  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1512  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1504  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1509  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1421  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1506  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff  36  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1502  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff   6  attempt 2  saw 19 active  -> deactivated
staff 1507  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1503  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff  27  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1510  attempt 1  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1511  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1436  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1508  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1512  attempt 2  saw 18 active  -> deactivated
staff 1504  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1505  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1501  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1514  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1509  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1502  attempt 3  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1471  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1506  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1507  attempt 3  saw 16 active  -> deactivated
staff 1421  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff  36  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff  27  attempt 3  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1436  attempt 3  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1503  attempt 2  saw 17 active  -> deactivated
staff 1510  attempt 2  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1511  attempt 3  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1505  attempt 3  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1504  attempt 3  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1501  attempt 3  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1509  attempt 3  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1514  attempt 3  saw 15 active  -> deactivated
staff 1471  attempt 3  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff  36  attempt 3  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1502  attempt 4  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1421  attempt 3  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1436  attempt 4  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1508  attempt 3  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff  27  attempt 4  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1506  attempt 3  saw 14 active  -> deactivated
staff 1510  attempt 3  saw 13 active  -> deactivated
staff 1504  attempt 4  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1511  attempt 4  saw 12 active  -> deactivated
staff 1505  attempt 4  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1421  attempt 4  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1501  attempt 4  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1504  attempt 5  saw 11 active  -> deactivated
staff  36  attempt 4  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1436  attempt 5  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1509  attempt 4  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1471  attempt 4  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1502  attempt 5  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff  27  attempt 5  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1505  attempt 5  saw 10 active  -> deactivated
staff 1421  attempt 5  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1508  attempt 4  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1436  attempt 6  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff  27  attempt 6  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1501  attempt 5  saw  9 active  -> deactivated
staff  36  attempt 5  saw  8 active  -> deactivated
staff 1509  attempt 5  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1421  attempt 6  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1502  attempt 6  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff  27  attempt 7  saw  7 active  -> deactivated
staff 1436  attempt 7  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1509  attempt 6  saw  6 active  -> deactivated
staff 1502  attempt 7  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1471  attempt 5  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1508  attempt 5  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1421  attempt 7  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1436  attempt 8  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1508  attempt 6  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1421  attempt 8  saw  4 active  -> deactivated
staff 1471  attempt 6  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1502  attempt 8  saw  5 active  -> deactivated
staff 1436  attempt 9  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during commit attempt.)
staff 1436  attempt 10  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1508  attempt 7  saw  3 active  -> deactivated
staff 1471  attempt 7  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1436  attempt 11  saw  2 active  -> deactivated
staff 1471  attempt 8  40001 serialization failure, retrying (Reason code: Canceled on identification as a pivot, during write.)
staff 1471  attempt 9  saw  1 active  -> stayed active
Deactivated: 19, retries: 79
Active staff in store 1 afterwards: 1
OK: rule kept
```

</details>

As linhas são escritas depois do commit (ou do erro) de cada tentativa, por isso a ordem no output não é exatamente a ordem dos commits (por exemplo, "saw 4" aparece antes de "saw 5").

### Porque é que `READ COMMITTED` viola a regra

A regra ("pelo menos 1 ativo por loja") depende de **várias linhas**, mas cada transação só **escreve uma**, e cada uma escreve uma linha diferente.

- Em `READ COMMITTED`, cada instrução vê os dados que já tinham commit quando começou. Por causa da barreira, as 20 contagens correm antes de qualquer `UPDATE`, por isso as 20 threads veem `20` e decidem desativar-se.
- Os 20 `UPDATE` alteram 20 linhas diferentes. Não há duas transações a pedir o lock da mesma linha, por isso nenhuma espera e nenhuma volta a ler nada. (No lost update, o `UPDATE` atómico funcionava porque as duas sessões escreviam a **mesma** linha. Aqui não há esse ponto de encontro.)
- Não há nenhuma constraint sobre o conjunto: um `CHECK` só vê uma linha de cada vez.

Cada transação, sozinha, está correta: viu mais de 1 ativo e desativou um. O erro está na combinação: a decisão de cada uma assenta numa leitura que as outras invalidaram ao escrever. É isto o *write skew*. Resultado: 0 ativos.

### Porque é que `SERIALIZABLE` não viola a regra

`SERIALIZABLE` garante que o resultado é igual ao de **alguma ordem em série** das transações que fizeram commit. Em série, cada transação veria as desativações das anteriores, e a última veria `1` e não se desativava. O PostgreSQL implementa isto com *Serializable Snapshot Isolation* (SSI):

- O `count(*)` regista **SIRead locks** sobre o que leu (as linhas, páginas ou a tabela `staff`). Estes locks não bloqueiam ninguém, só registam a leitura.
- Quando a thread X escreve uma linha que a thread Y leu (e vice-versa), o Postgres regista uma dependência *rw* entre as duas. Com 20 transações que leram todas as linhas e escreveram uma cada, formam-se ciclos de dependências que nenhuma ordem em série consegue explicar.
- Quando uma transação fica no meio de duas dependências destas (o *pivot*), o Postgres cancela-a com SQLSTATE `40001` (`could not serialize access due to read/write dependencies among transactions`). O `Reason code` no output diz se foi detetado na escrita (`during write`) ou no commit (`during commit attempt`).
- Na primeira ronda só uma transação (staff 1513) fez commit. As outras 19 falharam. Cada retry começa uma transação nova, com um snapshot novo, e conta os ativos **depois** dos commits anteriores (19, 18, ...). Os retries não usam barreira, mas continuam concorrentes entre si, por isso também há conflitos e mais retries (79 no total). Isto não é um problema: cada transação que falha é desfeita por inteiro, e só ficam as que são compatíveis com uma ordem em série.
- A última thread (1471) contou `1` e não alterou nada. Ficou exatamente 1 membro ativo.

O preço é o retry: em `SERIALIZABLE` a aplicação **tem** de estar preparada para repetir a transação toda (incluindo a leitura) quando recebe `40001`. Repetir só o `UPDATE` reutilizaria uma contagem desatualizada.

Alternativas em `READ COMMITTED`: serializar à mão quem decide pela mesma loja, por exemplo com `SELECT ... FROM store WHERE store_id = 1 FOR UPDATE` antes da contagem (todas as transações passam a esperar pela mesma linha), ou `SELECT ... FROM staff WHERE store_id = 1 AND active FOR UPDATE`.
