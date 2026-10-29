# Exercício 07: Indexes and optimisation

## Enunciado

Folder: `exercises/07-indexes/exercise/`

**Goal.** Read query plans, create indexes that a measured query needs, and recognise when an index cannot help.

**Starting point.** An empty database (`./scripts/create-db.sh ex07 --reset`) with the `big_rental` table of the tutorial, created by this script (`setup.sql`):

```sql
SELECT setseed(0.1);
CREATE TABLE big_rental AS
SELECT g AS id,
       (random() * 599 + 1)::int                 AS customer_id,
       now() - random() * interval '3 years'      AS rented_at,
       CASE WHEN random() < 0.03 THEN NULL ELSE now() END AS returned_at
FROM generate_series(1, 2000000) AS g;
VACUUM ANALYZE big_rental;
```

The table has no indexes at the start. Analyse these 5 queries:

```sql
-- Q1
SELECT count(*) FROM big_rental WHERE customer_id = 42 AND returned_at IS NULL;

-- Q2
SELECT * FROM big_rental WHERE rented_at >= now() - interval '1 day' ORDER BY rented_at;

-- Q3
SELECT * FROM big_rental WHERE rented_at::date = current_date - 10;

-- Q4
SELECT customer_id, count(*) FROM big_rental WHERE returned_at IS NOT NULL GROUP BY customer_id;

-- Q5
SELECT * FROM big_rental
WHERE customer_id IN (7, 42, 99) AND rented_at >= now() - interval '30 days'
ORDER BY rented_at DESC;
```

**Tasks.**

1. For each query, explain in one or two sentences what it returns.
2. Run `EXPLAIN (ANALYZE, BUFFERS)` on each query without indexes. Run it 3 times and keep the median execution time.
3. For each query, create the index you think it needs and run the same `EXPLAIN` again. Name the plan node used before and after (`Seq Scan`, `Index Scan`, `Index Only Scan`, `Bitmap Heap Scan`).
4. Not every query can be made faster by an index as it is written. When an index does not help, prove it with the plans and explain why. If rewriting the query lets an index help, show the rewritten query and its plan.
5. Measure the write cost: time `INSERT INTO big_rental SELECT g, 1, now(), NULL FROM generate_series(2000001, 2100000) g;` on a table with no indexes and on a table with all your indexes (recreate the table with `setup.sql` between runs).

**Deliverables.**

- `setup.sql`, and `indexes.sql` with every `CREATE INDEX` you kept.
- `README.md` with, for each query: what it does, the key lines of the plan before, the index created (or "none"), the key lines of the plan after, the median times before and after, and one or two sentences explaining the difference. Then the two insert times and an explanation of the difference.

**Done when.** Every query has plans before and after, every index is justified by a measured improvement, and every query that an index cannot speed up is explained with its plan.

## Challenge (obrigatório, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [x] `setup.sql` and `indexes.sql`
- [x] Q1 to Q5: what it does, plan before, index (or "none"), plan after, median times, explanation
- [x] Queries an index cannot fix proved with plans (and rewritten query if applicable)
- [x] Write cost: insert times without and with indexes, explained

## Resolução

Ficheiros entregues:

- [setup.sql](setup.sql): cria a `big_rental` (2 000 000 linhas, sem índices). Começa com `DROP TABLE IF EXISTS`, para poder correr outra vez.
- [indexes.sql](indexes.sql): os 3 índices mantidos.
- [analysis.sql](analysis.sql): todos os `EXPLAIN`, os índices testados, a Q3 reescrita, a Q4 com o índice forçado e o `INSERT` da tarefa 5.

### Como correr

A partir da root do repositório:

```bash
./scripts/create-db.sh ex07 --reset
psql -d ex07 -v ON_ERROR_STOP=1 -f exercises/07-indexes/exercise/setup.sql
psql -d ex07 -v ON_ERROR_STOP=1 -f exercises/07-indexes/exercise/analysis.sql
```

Todos os tempos são a mediana de 3 execuções de `EXPLAIN (ANALYZE, BUFFERS)` (PostgreSQL 18.6, `work_mem` 4MB). Cada índice foi testado sozinho, com `DROP INDEX` entre testes. A coluna "Depois" usa os 3 índices de `indexes.sql`, criados ao mesmo tempo.

### Resumo

| # | Índice | Nó antes | Nó depois | Antes | Depois |
|---|--------|----------|-----------|------:|-------:|
| Q1 | `(customer_id) WHERE returned_at IS NULL` | Parallel Seq Scan | Index Only Scan | 20.2 ms | 0.08 ms |
| Q2 | `(rented_at)` | Parallel Seq Scan + Sort | Bitmap Heap Scan + Sort | 52.4 ms | 2.9 ms |
| Q3 | none (como está escrita) | Parallel Seq Scan | Parallel Seq Scan | 52.1 ms | 46.5 ms |
| Q3 reescrita | `(rented_at)` (o da Q2) | Parallel Seq Scan | Bitmap Heap Scan | 35.7 ms | 2.7 ms |
| Q4 | none | Parallel Seq Scan | Parallel Seq Scan | 70.0 ms | 68.9 ms |
| Q5 | `(customer_id, rented_at)` | Parallel Seq Scan + Sort | Bitmap Heap Scan + Sort | 34.9 ms | 0.81 ms |

### Q1

```sql
SELECT count(*) FROM big_rental WHERE customer_id = 42 AND returned_at IS NULL;
```

**O que faz.** Conta os alugueres do cliente 42 que ainda não foram devolvidos (`returned_at` a `NULL`). Devolve uma linha com o número 93.

**Antes** (20.2 ms):

```
Parallel Seq Scan on big_rental  (rows=31.00 loops=3)
  Filter: ((returned_at IS NULL) AND (customer_id = 42))
  Rows Removed by Filter: 666636
  Buffers: shared hit=3432 read=9304
```

**Índices testados:**

| Índice | Tamanho | Nó | Tempo |
|--------|--------:|----|------:|
| `(customer_id)` | 14 MB | Bitmap Heap Scan (3 247 linhas descartadas pelo filtro) | 3.7 ms |
| `(customer_id, returned_at)` | 14 MB | Index Only Scan | 0.045 ms |
| `(customer_id) WHERE returned_at IS NULL` | 432 kB | Index Only Scan | 0.055 ms |

**Índice mantido:** `big_rental_customer_open_idx ON big_rental (customer_id) WHERE returned_at IS NULL`.

**Depois** (0.08 ms):

```
Index Only Scan using big_rental_customer_open_idx on big_rental  (rows=93.00 loops=1)
  Index Cond: (customer_id = 42)
  Heap Fetches: 0
  Buffers: shared hit=3
```

**Explicação.** Sem índice, o Postgres lê as 12 736 páginas da tabela para encontrar 93 linhas. Só com `customer_id`, o índice encontra as 3 340 linhas do cliente, mas depois tem de ir à tabela ver o `returned_at` de cada uma (2 930 páginas). O índice parcial guarda só as ~60 000 linhas com `returned_at IS NULL` (3% da tabela), por isso já responde às duas condições. Como o `count(*)` não precisa de outras colunas, o plano é um Index Only Scan que lê 3 páginas. O índice composto é igualmente rápido, mas ocupa 14 MB em vez de 432 kB.

### Q2

```sql
SELECT * FROM big_rental WHERE rented_at >= now() - interval '1 day' ORDER BY rented_at;
```

**O que faz.** Devolve todos os alugueres feitos nas últimas 24 horas, do mais antigo para o mais recente (cerca de 1 880 linhas).

**Antes** (52.4 ms):

```
Sort  Sort Key: rented_at  Sort Method: quicksort  Memory: 49kB
  ->  Parallel Seq Scan on big_rental  (rows=626.67 loops=3)
        Filter: (rented_at >= (now() - '1 day'::interval))
        Rows Removed by Filter: 666040
        Buffers: shared hit=4278 read=8458
```

**Índice:** `big_rental_rented_at_idx ON big_rental (rented_at)`.

**Depois** (2.9 ms):

```
Sort  Sort Key: rented_at  Sort Method: quicksort  Memory: 122kB
  ->  Bitmap Heap Scan on big_rental  (rows=1879.00 loops=1)
        Recheck Cond: (rented_at >= (now() - '1 day'::interval))
        Heap Blocks: exact=1740
        ->  Bitmap Index Scan on big_rental_rented_at_idx
              Index Cond: (rented_at >= (now() - '1 day'::interval))
              Buffers: shared hit=8
```

**Explicação.** O índice encontra logo o intervalo do último dia (8 páginas de índice), e deixa de ser preciso ler 2 milhões de linhas. O Sort continua lá. As datas foram geradas ao acaso, por isso as ~1 900 linhas estão espalhadas por ~1 700 páginas diferentes. O planner prefere juntá-las num bitmap e ler cada página uma vez por ordem física, e depois ordenar 122 kB em memória, a fazer um Index Scan que já vem ordenado mas salta para uma página diferente em cada linha.

### Q3

```sql
SELECT * FROM big_rental WHERE rented_at::date = current_date - 10;
```

**O que faz.** Devolve todos os alugueres feitos no dia de há 10 dias, de qualquer hora desse dia (1 838 linhas).

**Antes** (52.1 ms):

```
Parallel Seq Scan on big_rental  (rows=612.67 loops=3)
  Filter: ((rented_at)::date = (CURRENT_DATE - 10))
  Rows Removed by Filter: 666054
```

**Índice:** none para a query como está escrita.

**Depois, com `big_rental_rented_at_idx` já criado** (46.5 ms, o mesmo plano):

```
Parallel Seq Scan on big_rental  (rows=612.67 loops=3)
  Filter: ((rented_at)::date = (CURRENT_DATE - 10))
  Rows Removed by Filter: 666054
  Buffers: shared hit=12712
```

**Porque é que o índice não ajuda.** O índice guarda valores de `rented_at`, mas o `WHERE` compara `rented_at::date`, uma expressão calculada a partir da coluna. O planner não consegue usar um índice na coluna para uma condição sobre uma função dela, por isso calcula o cast em cada uma das 2 milhões de linhas. A queda de 52 para 46 ms vem só da cache, porque agora todas as páginas estão em `shared hit`. A alternativa seria um índice de expressão, mas falha:

```
CREATE INDEX ON big_rental ((rented_at::date));
ERROR:  functions in index expression must be marked IMMUTABLE
```

`rented_at` é `timestamptz`, e o dia a que um instante pertence depende do `TimeZone` da sessão. Por isso a conversão não é `IMMUTABLE` e não pode ir para um índice.

**Query reescrita.** A condição passa a ser um intervalo sobre a coluna sem conversão. Devolve as mesmas 1 838 linhas (confirmado com `count(*)` nas duas versões):

```sql
SELECT * FROM big_rental
WHERE rented_at >= (current_date - 10)::timestamptz
  AND rented_at <  (current_date - 9)::timestamptz;
```

Sem índice: 35.7 ms (Parallel Seq Scan, já mais rápida porque não faz o cast em cada linha). Com `big_rental_rented_at_idx`: 2.7 ms.

```
Bitmap Heap Scan on big_rental  (rows=1838.00 loops=1)
  Recheck Cond: ((rented_at >= ((CURRENT_DATE - 10))::timestamp with time zone) AND (rented_at < ((CURRENT_DATE - 9))::timestamp with time zone))
  Heap Blocks: exact=1701
  ->  Bitmap Index Scan on big_rental_rented_at_idx
        Buffers: shared hit=8
```

### Q4

```sql
SELECT customer_id, count(*) FROM big_rental WHERE returned_at IS NOT NULL GROUP BY customer_id;
```

**O que faz.** Para cada cliente, conta os alugueres já devolvidos. Devolve 600 linhas, uma por cliente.

**Antes** (70.0 ms com a cache quente; 78.2 ms na primeira medição, com leituras de disco):

```
Finalize GroupAggregate
  ->  Gather Merge
        ->  Sort  Sort Key: customer_id
              ->  Partial HashAggregate
                    ->  Parallel Seq Scan on big_rental  (rows=646640.00 loops=3)
                          Filter: (returned_at IS NOT NULL)
                          Rows Removed by Filter: 20027
```

**Índice:** none.

**Depois, com os índices testados:**

| Índice | Escolhido pelo planner? | Plano forçado (`SET enable_seqscan = off`) | Tempo forçado |
|--------|-------------------------|--------------------------------------------|--------------:|
| `(returned_at)` | não, mantém o Seq Scan (69.5 ms) | Parallel Index Scan | 79.6 ms |
| `(customer_id) WHERE returned_at IS NOT NULL` | não, mantém o Seq Scan (69.0 ms) | Parallel Index Only Scan | 67.1 ms |

**Porque é que o índice não ajuda.** O filtro deixa passar 1 939 920 das 2 000 000 linhas (97%). Um índice serve para encontrar poucas linhas sem ler a tabela toda, mas aqui a query precisa de quase todas. Com `(returned_at)`, o Postgres percorre o índice e salta para a tabela em cada linha, o que fica mais lento do que ler a tabela por ordem (79.6 contra 70 ms). O índice parcial permite um Index Only Scan, mas tem de ler as mesmas ~1,9 milhões de entradas e agregar na mesma. Ganha cerca de 3 ms, o que está dentro do ruído, à custa de 13 MB e de mais trabalho em cada escrita. Nenhum dos dois justifica ficar.

### Q5

```sql
SELECT * FROM big_rental
WHERE customer_id IN (7, 42, 99) AND rented_at >= now() - interval '30 days'
ORDER BY rented_at DESC;
```

**O que faz.** Devolve os alugueres dos clientes 7, 42 e 99 nos últimos 30 dias, do mais recente para o mais antigo (295 linhas).

**Antes** (34.9 ms):

```
Sort  Sort Key: rented_at DESC
  ->  Parallel Seq Scan on big_rental  (rows=98.33 loops=3)
        Filter: ((customer_id = ANY ('{7,42,99}'::integer[])) AND (rented_at >= (now() - '30 days'::interval)))
        Rows Removed by Filter: 666568
```

**Índices testados:**

| Índice | Buffers no índice | Tempo |
|--------|------------------:|------:|
| `(customer_id, rented_at)` | 11 | 0.73 ms |
| `(rented_at, customer_id)` | 222 | 1.9 ms |

**Índice mantido:** `big_rental_customer_rented_at_idx ON big_rental (customer_id, rented_at)`.

**Depois** (0.81 ms):

```
Sort  Sort Key: rented_at DESC  Sort Method: quicksort  Memory: 36kB
  ->  Bitmap Heap Scan on big_rental  (rows=295.00 loops=1)
        Recheck Cond: ((customer_id = ANY ('{7,42,99}'::integer[])) AND (rented_at >= (now() - '30 days'::interval)))
        Heap Blocks: exact=290
        ->  Bitmap Index Scan on big_rental_customer_rented_at_idx
              Index Cond: ((customer_id = ANY ('{7,42,99}'::integer[])) AND (rented_at >= (now() - '30 days'::interval)))
              Index Searches: 3
              Buffers: shared hit=11
```

**Explicação.** Com a coluna da igualdade primeiro, o índice faz 3 pesquisas (`Index Searches: 3`), uma por cliente, e em cada uma lê só a parte com os últimos 30 dias. Com a ordem inversa, tem de percorrer as entradas de todos os clientes dos últimos 30 dias (222 páginas) para ficar com 3 deles. O Sort continua, porque o índice está ordenado por `rented_at` dentro de cada cliente, e não no conjunto dos 3 clientes. Ordenar 295 linhas em memória custa muito pouco.

### Custo de escrita

```sql
INSERT INTO big_rental SELECT g, 1, now(), NULL FROM generate_series(2000001, 2100000) g;
```

A tabela foi recriada com `setup.sql` antes de cada execução, e com `indexes.sql` no segundo caso. Antes do `INSERT` corri um `CHECKPOINT`.

| Tabela | Execuções | Mediana |
|--------|-----------|--------:|
| Sem índices | 27.3 / 28.2 / 27.9 ms | 27.9 ms |
| Com os 3 índices | 131.1 / 134.5 / 133.5 ms | 133.5 ms |

**Explicação.** Com os índices, o mesmo `INSERT` de 100 000 linhas demora cerca de 4,8 vezes mais. Sem índices, cada linha nova vai só para o fim da tabela. Com índices, cada linha também tem de ser inserida, na posição certa, em cada B-tree que a inclui. Neste `INSERT` são os três: todas as linhas têm `returned_at` a `NULL`, por isso entram também no índice parcial da Q1. Cada índice é mais escrita e mais WAL. Por isso um índice só deve ficar quando melhora uma query de forma medida, e foi por essa razão que os índices da Q4 foram removidos.
