# Challenge 06: Queries II, window functions and views

Obrigatório.

## Enunciado

Folder: `exercises/06-window/challenge/`

**Goal.** Solve a "gaps and islands" problem with window functions.

**Starting point.** A fresh copy of Pagila (`./scripts/create-db.sh ch06 --pagila --reset`). An island is a run of consecutive calendar months in which a customer rented at least one film. In Pagila, March and April 2022 have no rentals at all.

**Tasks.**

1. For each customer, find their longest island: `customer_id`, `first_month`, `last_month`, `months`. When a customer has two islands of the same length, keep the earliest.
2. Return the 10 customers with the longest islands, longest first, ties broken by `customer_id`.
3. Use window functions and set operations only: no procedural code, no recursive CTE.

**Deliverables.**

- `islands.sql` with the query.
- `README.md` with the 10 rows of the result and an explanation of the technique you used to group consecutive months.

**Done when.** The first row is customer 70 with 19 months, from 2023-06 to 2024-12, and the tenth row is customer 556 with 16 months.

## Resposta

Ficheiro: [islands.sql](islands.sql). A partir da root do repositório:

```bash
./scripts/create-db.sh ch06 --pagila --reset
psql -d ch06 -v ON_ERROR_STOP=1 -f exercises/06-window/challenge/islands.sql
```

### Resultado

```
 customer_id | first_month | last_month | months
-------------+-------------+------------+--------
          70 | 2023-06     | 2024-12    |     19
         547 | 2022-05     | 2023-10    |     18
         567 | 2022-06     | 2023-11    |     18
          33 | 2023-07     | 2024-11    |     17
         158 | 2022-11     | 2024-03    |     17
         299 | 2022-05     | 2023-09    |     17
         443 | 2023-07     | 2024-11    |     17
         533 | 2023-04     | 2024-08    |     17
         740 | 2024-07     | 2025-11    |     17
         556 | 2023-09     | 2024-12    |     16
```

A primeira linha é o cliente 70 com 19 meses, de 2023-06 a 2024-12, e a décima é o cliente 556 com 16 meses, como pede o enunciado.

### O que a query faz

1. **Meses com atividade**: `select distinct customer_id, date_trunc('month', rental_date)::date` dá uma linha por cliente e por mês em que alugou pelo menos um filme. O `distinct` garante que vários alugueres no mesmo mês contam como um só mês.
2. **Mês como número**: `month_n = ano * 12 + mês`. Assim, dois meses de calendário consecutivos diferem sempre exatamente 1, também de dezembro para janeiro.
3. **Numeração**: `rn = row_number() over (partition by customer_id order by month)` numera os meses de cada cliente por ordem: 1, 2, 3, ...
4. **Ilhas**: `group by customer_id, month_n - rn`, com `min(month)`, `max(month)` e `count(*)` para o primeiro mês, o último e o número de meses de cada ilha.
5. **Ilha mais longa de cada cliente**: `row_number() over (partition by customer_id order by months desc, first_month)` e `rn = 1`. Em caso de empate fica a ilha mais antiga.
6. **Top 10**: `order by months desc, customer_id limit 10`.

### A técnica para agrupar meses consecutivos

Dentro de uma sequência de meses consecutivos, `month_n` e `rn` sobem os dois 1 de cada vez, por isso a diferença `month_n - rn` fica igual. Quando há um buraco, `month_n` salta mais do que 1 e `rn` sobe só 1, por isso a diferença aumenta e começa um grupo novo. Cada valor de `month_n - rn` é uma ilha.

Exemplo com o cliente 70:

```
  month  | month_n | rn |  grp
---------+---------+----+-------
 2022-09 |   24273 |  5 | 24268
 2022-10 |   24274 |  6 | 24268
 2022-12 |   24276 |  7 | 24269   <- falta 2022-11: começa uma ilha nova
 2023-01 |   24277 |  8 | 24269
 2023-02 |   24278 |  9 | 24269
 2023-04 |   24280 | 10 | 24270   <- falta 2023-03
 2023-06 |   24282 | 11 | 24271   <- falta 2023-05: começa a ilha de 19 meses
 2023-07 |   24283 | 12 | 24271
```

Março e abril de 2022 não têm alugueres nenhuns, por isso nenhuma ilha os atravessa: o `month_n` salta 3 e o grupo muda. A query só usa window functions (`row_number()`) e agregação, sem código procedural nem CTE recursivo.
