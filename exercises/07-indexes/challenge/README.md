# Challenge 07: Indexes and optimisation

Obrigatório.

## Enunciado

Folder: `exercises/07-indexes/challenge/`

**Goal.** Compare `OFFSET` pagination with keyset pagination, and connect index only scans to `VACUUM`.

**Starting point.** The `big_rental` table of the exercise above, created with its `setup.sql` in a database of its own (`./scripts/create-db.sh ch07 --reset`). Pages are 20 rows of the whole table ordered by `rented_at DESC, id DESC`. Page 5,000 starts after 99,980 rows.

**Tasks.**

1. Create an index that matches the sort order.
2. Read page 5,000 with `ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20` and record its plan and time with `EXPLAIN (ANALYZE, BUFFERS)`.
3. Read the same page with keyset pagination. Store the last row of page 4,999 in psql variables, then use them:

   ```sql
   SELECT rented_at AS last_rented_at, id AS last_id
   FROM big_rental ORDER BY rented_at DESC, id DESC OFFSET 99979 LIMIT 1 \gset

   SELECT id, rented_at, customer_id FROM big_rental
   WHERE (rented_at, id) < (:'last_rented_at', :last_id)
   ORDER BY rented_at DESC, id DESC LIMIT 20;
   ```

   Show that both queries return the same 20 rows, and compare the plans and times.
4. Recreate the index with `INCLUDE (customer_id)` so that the keyset query becomes an `Index Only Scan`.
5. Run `UPDATE big_rental SET customer_id = customer_id WHERE id % 50 = 0;`, run the keyset query again and read the `Heap Fetches` line. Then run `VACUUM big_rental;` and run it once more.

**Deliverables.**

- `pagination.sql` with every statement in order.
- `README.md` with the plans and times of tasks 2, 3 and 5, and an explanation of why `OFFSET` gets slower as the page number grows, and of what `VACUUM` changes in the visibility map that makes `Heap Fetches` drop.

**Done when.** The two methods return the same rows, the keyset query does not depend on the page number, the plan of task 4 is an `Index Only Scan`, and `Heap Fetches` is above 0 after the update and 0 after `VACUUM`.

## Resolução

Ficheiros entregues:

- [pagination.sql](pagination.sql): todos os comandos das tarefas 1 a 5, por ordem.
- `README.md`: este ficheiro, com os planos e os tempos das tarefas 2 a 5 e as duas explicações.

### Como correr

A partir da root do repositório:

```bash
./scripts/create-db.sh ch07 --reset
psql -d ch07 -v ON_ERROR_STOP=1 -f exercises/07-indexes/exercise/setup.sql
psql -d ch07 -v ON_ERROR_STOP=1 -f exercises/07-indexes/challenge/pagination.sql
```

Tem de correr com o `psql`, porque a tarefa 3 usa `\gset`. O ficheiro pode correr mais do que uma vez: a tarefa 1 começa com `DROP INDEX IF EXISTS`.

Os tempos são a mediana de 3 execuções de `EXPLAIN (ANALYZE, BUFFERS)` (PostgreSQL 18.6). A primeira execução de cada query é quase sempre mais lenta, porque as páginas ainda não estão em cache.

### Resumo

| Tarefa | Índice | Plano | Linhas lidas | Buffers | Tempo (mediana) | Heap Fetches |
|---|---|---|---:|---:|---:|---:|
| 2: `OFFSET 99980` | `(rented_at DESC, id DESC)` | Index Scan | 100 000 | 100 377 | 32.9 ms | n/a |
| 3: keyset | `(rented_at DESC, id DESC)` | Index Scan | 20 | 23 | 0.013 ms | n/a |
| 4: keyset | `... INCLUDE (customer_id)` | Index Only Scan | 20 | 4 | 0.008 ms | 0 |
| 5: depois do `UPDATE` | `... INCLUDE (customer_id)` | Index Only Scan | 20 | 24 | 0.012 ms | 20 |
| 5: depois do `VACUUM` | `... INCLUDE (customer_id)` | Index Only Scan | 20 | 4 | 0.008 ms | 0 |

### 1. Índice com a ordem da paginação

```sql
CREATE INDEX big_rental_rented_at_id_idx ON big_rental (rented_at DESC, id DESC);
```

As colunas e o sentido são os mesmos do `ORDER BY rented_at DESC, id DESC`. O Postgres lê o índice do início para o fim e as linhas já saem pela ordem certa, por isso nenhum dos planos tem um nó Sort. O `id` desempata as linhas com o mesmo `rented_at`, para que a ordem seja sempre a mesma e nenhuma linha apareça em duas páginas nem fique de fora.

### 2. Página 5 000 com `OFFSET`

```sql
SELECT id, rented_at, customer_id FROM big_rental
ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20;
```

Tempos: 107.8 / 32.9 / 31.6 ms. A mediana é **32.9 ms**.

```
Limit  (actual time=31.617..31.624 rows=20.00 loops=1)
  Buffers: shared hit=100377
  ->  Index Scan using big_rental_rented_at_id_idx on big_rental  (actual time=0.006..29.898 rows=100000.00 loops=1)
        Index Searches: 1
        Buffers: shared hit=100377
```

O Index Scan devolve **100 000 linhas** ao `Limit`, que deita fora as primeiras 99 980 e fica com 20. Também lê 100 377 páginas (buffers): quase uma por linha, porque cada linha está numa página diferente da tabela.

### 3. Página 5 000 com keyset pagination

```sql
SELECT rented_at AS last_rented_at, id AS last_id
FROM big_rental ORDER BY rented_at DESC, id DESC OFFSET 99979 LIMIT 1 \gset

SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;
```

**As duas formas de paginar devolvem as mesmas linhas.** Os dois `EXCEPT` do `pagination.sql` (`OFFSET EXCEPT keyset` e `keyset EXCEPT OFFSET`) dão cada um `(0 rows)`.

Tempos: 0.067 / 0.013 / 0.012 ms. A mediana é **0.013 ms**.

```
Limit  (actual time=0.004..0.010 rows=20.00 loops=1)
  Buffers: shared hit=23
  ->  Index Scan using big_rental_rented_at_id_idx on big_rental  (actual time=0.004..0.009 rows=20.00 loops=1)
        Index Cond: (ROW(rented_at, id) < ROW('2026-09-06 00:06:24.463437+00'::timestamp with time zone, 13584))
        Index Searches: 1
        Buffers: shared hit=23
```

**Comparação com a tarefa 2.** O plano é o mesmo, um Index Scan sobre o mesmo índice. A diferença é que a condição `(rented_at, id) < (...)` passou a ser um `Index Cond`. O Postgres desce diretamente pela B-tree até à última linha da página 4 999 e lê só as 20 seguintes. Em vez de 100 000 linhas e 100 377 buffers, lê 20 linhas e 23 buffers, e fica cerca de 2 500 vezes mais rápido (32.9 ms contra 0.013 ms).

**O tempo da keyset não depende do número da página.** A mesma query keyset, medida a partir de várias páginas (mediana de 3 execuções):

| Página | `OFFSET` | Keyset |
|---:|---:|---:|
| 1 | 0.009 ms | n/a |
| 2 | n/a | 0.015 ms |
| 50 | 0.189 ms | n/a |
| 500 | 1.94 ms | n/a |
| 5 000 | 29.5 ms | 0.024 ms |
| 25 000 | 167.1 ms | n/a |
| 50 000 | 368.8 ms | 0.013 ms |
| 100 000 (última) | 763.7 ms | 0.011 ms |

### Porque é que o `OFFSET` fica mais lento à medida que a página cresce

O `OFFSET` não sabe onde começa a página N. Um índice B-tree permite encontrar depressa um **valor**, mas não uma **posição**: não guarda quantas linhas há antes de cada entrada. Para devolver a página N, o Postgres tem de percorrer o índice desde o início, ir buscar cada uma das `(N - 1) × 20` linhas anteriores e deitá-las fora no nó `Limit`. O trabalho é proporcional ao número da página. A tabela acima mostra isso: cada vez que o `OFFSET` fica 10 vezes maior, o tempo também fica cerca de 10 vezes maior, até 764 ms na última página.

A keyset troca a posição por um valor. "As 20 linhas a seguir a `(rented_at, id)`" é uma condição que a B-tree resolve com uma descida até ao ponto certo, seguida da leitura de 20 entradas. Por isso custa o mesmo na página 2 e na página 100 000. A desvantagem é que não permite saltar para uma página qualquer, por exemplo da página 3 diretamente para a 5 000: só deixa avançar a partir da última linha que já foi mostrada.

### 4. Index Only Scan com `INCLUDE`

```sql
DROP INDEX IF EXISTS big_rental_rented_at_id_idx;
CREATE INDEX big_rental_rented_at_id_idx
ON big_rental (rented_at DESC, id DESC) INCLUDE (customer_id);
VACUUM ANALYZE big_rental;
```

Tempos: 0.038 / 0.008 / 0.007 ms. A mediana é **0.008 ms**.

```
Limit  (actual time=0.004..0.005 rows=20.00 loops=1)
  Buffers: shared hit=4
  ->  Index Only Scan using big_rental_rented_at_id_idx on big_rental  (actual time=0.004..0.004 rows=20.00 loops=1)
        Index Cond: (ROW(rented_at, id) < ROW('2026-09-06 00:06:24.463437+00'::timestamp with time zone, 13584))
        Heap Fetches: 0
        Index Searches: 1
        Buffers: shared hit=4
```

A query pede `id`, `rented_at` e `customer_id`. Na tarefa 3 o índice só tinha as duas primeiras colunas, por isso o Postgres ia à tabela buscar o `customer_id` de cada linha (23 buffers). Com o `INCLUDE`, o `customer_id` fica guardado nas folhas do índice, sem fazer parte da ordenação. Agora o índice tem todas as colunas que a query pede, e o plano passa a ser um **Index Only Scan** que lê 4 buffers.

### 5. Heap Fetches antes e depois do `VACUUM`

```sql
UPDATE big_rental SET customer_id = customer_id WHERE id % 50 = 0;   -- UPDATE 40000
```

**Depois do `UPDATE`.** Tempos: 0.067 / 0.012 / 0.009 ms. A mediana é **0.012 ms**.

```
Limit  (actual time=0.003..0.007 rows=20.00 loops=1)
  Buffers: shared hit=24
  ->  Index Only Scan using big_rental_rented_at_id_idx on big_rental  (actual time=0.003..0.006 rows=20.00 loops=1)
        Heap Fetches: 20
        Buffers: shared hit=24
```

**Depois de `VACUUM big_rental;`.** Tempos: 0.017 / 0.008 / 0.007 ms. A mediana é **0.008 ms**.

```
Limit  (actual time=0.004..0.005 rows=20.00 loops=1)
  Buffers: shared hit=4
  ->  Index Only Scan using big_rental_rented_at_id_idx on big_rental  (actual time=0.004..0.004 rows=20.00 loops=1)
        Heap Fetches: 0
        Buffers: shared hit=4
```

O plano é sempre um Index Only Scan. Depois do `UPDATE` há `Heap Fetches: 20`, uma ida à tabela por cada linha devolvida, e o número de buffers sobe de 4 para 24. Depois do `VACUUM`, volta a 0 heap fetches e 4 buffers. Para que o resultado não dependesse do autovacuum, desliguei-o na tabela durante a medição das 3 execuções depois do `UPDATE` (`ALTER TABLE big_rental SET (autovacuum_enabled = off)`), e voltei a ligá-lo no fim.

### O que o `VACUUM` muda no visibility map

O índice não guarda informação de visibilidade. Não sabe se uma entrada aponta para uma versão da linha que a transação atual pode ver, ou para uma versão antiga ou ainda não confirmada. Essa informação (`xmin`/`xmax`) só existe na tabela (o *heap*). Para não ter de ir sempre à tabela, o Postgres mantém o **visibility map**: 1 bit por página da tabela, que diz se *todas* as linhas dessa página são visíveis para todas as transações. No Index Only Scan, por cada entrada do índice, o Postgres consulta esse bit:

- se a página está marcada como **toda visível**, usa os valores do índice e não lê a tabela;
- se não está, vai à página da tabela confirmar a visibilidade da linha, e cada uma dessas idas conta como um **heap fetch**.

O `UPDATE` não muda nenhum valor, mas em PostgreSQL um `UPDATE` cria sempre uma nova versão da linha e marca a antiga como morta. Isso tira o bit de "toda visível" a todas as páginas onde mexeu. Com 1 linha atualizada em cada 50, e cerca de 157 linhas por página, praticamente todas as páginas da tabela perderam o bit. Por isso as 20 linhas da página deram 20 heap fetches.

O `VACUUM` remove as versões mortas e, nas páginas em que todas as linhas que restam são visíveis para todos, volta a ligar o bit no visibility map. A partir daí, o Index Only Scan volta a responder só a partir do índice, e os `Heap Fetches` descem para 0. Por isso, numa tabela com muitas escritas, o Index Only Scan só é realmente "only" se o (auto)vacuum acompanhar o ritmo das atualizações.
