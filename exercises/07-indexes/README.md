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

- [ ] `setup.sql` and `indexes.sql`
- [ ] Q1 to Q5: what it does, plan before, index (or "none"), plan after, median times, explanation
- [ ] Queries an index cannot fix proved with plans (and rewritten query if applicable)
- [ ] Write cost: insert times without and with indexes, explained

explicação do exercicio do professor:

- eplicar o que a que faz
- que indice é que as tabelas devem ter que a consulta seja optimizada
- caso a criação de index nao melhore a condição da consulta, explicar o porquê
