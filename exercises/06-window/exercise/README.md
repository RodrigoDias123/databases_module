# Exercício 06: Queries II, window functions and views

Ficheiros entregues:

- `README.md`: este ficheiro, com a contagem de linhas e as 5 primeiras linhas de cada resultado, e o output dos passos da tarefa 6.
- [queries.sql](queries.sql): as 6 tarefas, cada uma com um comentário com o número e a pergunta.

## Como correr

A partir da root do repositório, numa cópia limpa da Pagila:

```bash
./scripts/create-db.sh ex06 --pagila --reset
psql -d ex06 -v ON_ERROR_STOP=1 -f exercises/06-window/exercise/queries.sql
```

O `psql` usa as variáveis `PGHOST`, `PGUSER` e `PGPASSWORD` do devcontainer. O script pode correr mais do que uma vez: a tarefa 6 começa com `drop materialized view if exists` e apaga no fim o pagamento que insere. Tem de correr com o `psql`, porque a tarefa 6 usa `\gset`.

## Resumo

| # | Pergunta | Esperado | Obtido |
|---|----------|----------|--------|
| 1 | Os 3 filmes mais alugados de cada categoria, com empates | 56 linhas | ✅ 56 |
| 2 | Receita por dia em julho de 2026, com total acumulado | 28 linhas; último total 2409.88 | ✅ igual |
| 3 | Receita por mês com a variação face ao mês anterior | 55 linhas; julho de 2026: 2409.88, 304.15, 14.4% | ✅ igual |
| 4 | Posição de cada cliente no ranking da sua loja | 999 linhas; 468 em 1.º na loja 1 (344.06), 526 em 1.º na loja 2 (358.12) | ✅ igual |
| 5 | Os 5 melhores clientes de cada loja | 10 linhas | ✅ 10 |
| 6 | Vista materializada da receita mensal, com refresh | só muda depois do refresh | ✅ igual |

## Notas

- **1.** `dense_rank()` por categoria, num subquery, filtrado com `position <= 3` na query de fora. Uma window function não pode ser usada no `WHERE` nem no `HAVING` da mesma query, porque é calculada depois deles. Com `dense_rank()` os empatados partilham a posição e a seguinte não salta, por isso todos os filmes nas posições 1 a 3 aparecem (56 linhas). Com `rank()` dava 50.
- **2.** `sum(sum(amount)) over (order by day)`: a soma de dentro é a do `GROUP BY`, e a de fora é a window function, que acumula os dias por ordem.
- **3.** `lag(revenue) over (order by month)` dá a receita do mês anterior. O primeiro mês fica a `NULL`, porque não tem mês anterior.
- **4.** `LEFT JOIN` de `customer` para `payment` com `coalesce(sum(p.amount), 0)`, para que os clientes sem pagamentos entrem com 0. `rank()` por loja deixa os empatados com a mesma posição.
- **5.** O mesmo cálculo da tarefa 4, mas com `row_number()`, para dar exatamente 5 clientes por loja mesmo que haja um empate na 5.ª posição.
- **6.** O `unique index` em `month` é obrigatório para o `REFRESH MATERIALIZED VIEW CONCURRENTLY`. O `insert` e o `delete` não estão numa transação, porque o `REFRESH ... CONCURRENTLY` não pode correr dentro de uma. O `payment_id` do pagamento inserido é guardado com `\gset` para o apagar no fim.

## Output de cada query

### 1. Os 3 filmes mais alugados de cada categoria

56 linhas.

```
  category   |        title         | rentals | position
-------------+----------------------+---------+----------
 Action      | CAT CONEHEADS        |     123 |        1
 Action      | SEABISCUIT PUNK      |      96 |        2
 Action      | IDOLS SNATCHERS      |      92 |        3
 Animation   | GILMORE BOILED       |     102 |        1
 Animation   | GRIT CLOCKWORK       |     102 |        1
```

### 2. Receita por dia em julho de 2026

28 linhas; a última é `2026-07-28` com `running_total` 2409.88.

```
    day     | revenue | running_total
------------+---------+---------------
 2026-07-01 |   67.78 |         67.78
 2026-07-02 |   89.62 |        157.40
 2026-07-03 |   61.78 |        219.18
 2026-07-04 |   97.66 |        316.84
 2026-07-05 |   46.81 |        363.65
```

### 3. Receita por mês com a variação face ao mês anterior

55 linhas; `2026-07-01` tem 2409.88, variação de 304.15 e 14.4% (o mês anterior tem 2105.73).

```
   month    | revenue  | variation_value | variation_percentage
------------+----------+-----------------+----------------------
 2022-01-01 |  3094.78 |                 |
 2022-02-01 | 10164.97 |         7070.19 |                228.5
 2022-03-01 | 11413.86 |         1248.89 |                 12.3
 2022-04-01 | 10759.52 |         -654.34 |                 -5.7
 2022-05-01 | 11347.28 |          587.76 |                  5.5
```

### 4. Posição de cada cliente no ranking da sua loja

999 linhas; na loja 2 o primeiro é o cliente 526 com 358.12.

```
 customer_id | store_id | total_paid | position
-------------+----------+------------+----------
         468 |        1 |     344.06 |        1
         380 |        1 |     324.04 |        2
         368 |        1 |     323.17 |        3
         295 |        1 |     322.12 |        4
          22 |        1 |     320.17 |        5
```

### 5. Os 5 melhores clientes de cada loja

10 linhas.

```
 customer_id | store_id | total_paid | position
-------------+----------+------------+----------
         468 |        1 |     344.06 |        1
         380 |        1 |     324.04 |        2
         368 |        1 |     323.17 |        3
         295 |        1 |     322.12 |        4
          22 |        1 |     320.17 |        5
         526 |        2 |     358.12 |        1
         410 |        2 |     317.10 |        2
         120 |        2 |     315.12 |        3
         469 |        2 |     311.18 |        4
         178 |        2 |     304.17 |        5
```

### 6. Vista materializada da receita mensal

Receita de julho de 2026 em cada passo:

```
DROP MATERIALIZED VIEW
SELECT 55
CREATE INDEX

-- Antes
   month    | revenue
------------+---------
 2026-07-01 | 2409.88

-- Pagamento novo de 10.00 em 2026-07-15
INSERT 0 1

-- Sem refresh: não mudou
   month    | revenue
------------+---------
 2026-07-01 | 2409.88

REFRESH MATERIALIZED VIEW

-- Depois do refresh: inclui o pagamento novo
   month    | revenue
------------+---------
 2026-07-01 | 2419.88

-- Limpeza
DELETE 1
REFRESH MATERIALIZED VIEW
   month    | revenue
------------+---------
 2026-07-01 | 2409.88
```
