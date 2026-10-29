# Exercício 05: Queries I, joins, aggregation, subqueries and CTEs

Ficheiros entregues:

- `README.md`: este ficheiro, com a contagem de linhas e as 5 primeiras linhas de cada resultado.
- [queries.sql](queries.sql): as 10 queries, cada uma com um comentário com o número e a pergunta.

## Como correr

A partir da root do repositório, numa cópia limpa da Pagila:

```bash
./scripts/create-db.sh ex05 --pagila --reset
psql -d ex05 -v ON_ERROR_STOP=1 -f exercises/05-queries/exercise/queries.sql
```

O `psql` usa as variáveis `PGHOST`, `PGUSER` e `PGPASSWORD` do devcontainer. O script só tem `SELECT`s, por isso pode correr mais do que uma vez. Nenhuma query usa window functions.

## Resumo

| # | Pergunta | Esperado | Obtido |
|---|----------|----------|--------|
| 1 | Filmes por categoria, incluindo categorias sem filmes | 16 linhas; `Drama` e `Music` com 152 | ✅ igual |
| 2 | Receita por categoria e por mês em 2025 | 192 linhas; `Action` em janeiro de 2025 com 314.94 | ✅ igual |
| 3 | Filmes nunca alugados, incluindo os que não têm cópias | 42 linhas | ✅ 42 |
| 4 | Clientes que alugaram filmes das 5 classificações | 908 linhas | ✅ 908 |
| 5 | Pares de atores com mais de 3 filmes juntos (self join) | 143 linhas | ✅ 143 |
| 6 | Países com mais de 20 clientes | 7 linhas; `Mexico` com 430 | ✅ igual |
| 7 | Clientes que pagaram mais do que a média do seu país | 449 linhas | ✅ 449 |
| 8 | Filmes mais longos de cada classificação, com empates | 14 linhas | ✅ 14 |
| 9 | Clientes sem alugueres a partir de `2026-04-01` | 49 linhas | ✅ 49 |
| 10 | Média de dias fora por categoria | 16 linhas; `Sci-Fi` com 5.30 | ✅ igual |

## Notas

- **1.** `LEFT JOIN` com `count(fc.film_id)`: uma categoria sem filmes dava 0 e não 1. Nesta versão da Pagila todas as 16 têm filmes.
- **2.** O ano é filtrado com um intervalo semiaberto (`>= '2025-01-01' AND < '2026-01-01'`) e o mês sai de `date_trunc('month', payment_date)`, em UTC.
- **3.** `NOT EXISTS` sobre `inventory` juntado com `rental`. Assim entram os filmes sem cópias, e um filme aparece uma só vez mesmo que tenha várias cópias. Nesta Pagila, `LEFT JOIN ... IS NULL` também dá 42. Mas esse join olha para cada cópia: um filme alugado com uma cópia que nunca saiu entrava no resultado.
- **4.** `count(distinct f.rating)` comparado com o número de classificações que existem em `film`.
- **5.** `fa2.actor_id > fa1.actor_id` deixa cada par uma só vez e nunca junta um ator consigo mesmo.
- **6.** Os pagamentos são somados por cliente numa CTE antes do join. Juntar `payment` diretamente repetia cada cliente uma vez por pagamento e `count(*)` contava pagamentos em vez de clientes.
- **7.** O total de cada cliente vem de uma subquery correlacionada com `coalesce(..., 0)`, por isso os clientes sem pagamentos entram na média do país com 0.
- **8.** Subquery correlacionada com `max(length)` da mesma classificação; os empates ficam todos porque a comparação é `=`.
- **9.** `NOT EXISTS` com `rental_date >= '2026-04-01'`.
- **10.** `extract(epoch from return_date - rental_date) / 86400` converte o intervalo em dias com fração antes da média.

## Output de cada query

### 1. Filmes por categoria

16 linhas.

```
 category_id |  category   | films
-------------+-------------+-------
           7 | Drama       |   152
          12 | Music       |   152
          16 | Travel      |   151
           3 | Children    |   150
           9 | Foreign     |   150
```

### 2. Receita por categoria e por mês em 2025

192 linhas (16 categorias × 12 meses).

```
  category   |   month    | revenue
-------------+------------+---------
 Action      | 2025-01-01 |  314.94
 Action      | 2025-02-01 |  317.99
 Action      | 2025-03-01 |  370.90
 Action      | 2025-04-01 |  379.83
 Action      | 2025-05-01 |  384.76
```

### 3. Filmes nunca alugados

42 linhas.

```
 film_id |         title
---------+------------------------
      14 | ALICE FANTASIA
      33 | APOLLO TEEN
      36 | ARGONAUTS TOWN
      38 | ARK RIDGEMONT
      41 | ARSENIC INDEPENDENCE
```

### 4. Clientes que alugaram filmes das 5 classificações

908 linhas.

```
 customer_id | first_name  |  last_name
-------------+-------------+--------------
           1 | MARY        | SMITH
           2 | PATRICIA    | JOHNSON
           3 | LINDA       | WILLIAMS
           4 | BARBARA     | JONES
           5 | ELIZABETH   | BROWN
```

### 5. Pares de atores com mais de 3 filmes juntos

143 linhas.

```
 actor_id |        actor        | other_actor_id |    other_actor     | films
----------+---------------------+----------------+--------------------+-------
       27 | JULIA MCQUEEN       |             60 | HENRY BERRY        |     7
       15 | CUBA OLIVIER        |            198 | MARY KEITEL        |     6
       21 | KIRSTEN PALTROW     |            108 | WARREN NOLTE       |     6
       37 | VAL BOLGER          |            188 | ROCK DUKAKIS       |     6
       83 | BEN WILLIS          |            161 | HARVEY HOPE        |     6
```

### 6. Países com mais de 20 clientes

7 linhas.

```
      country       | customers |   paid
--------------------+-----------+----------
 Mexico             |       430 | 35650.03
 India              |        60 | 14182.51
 China              |        53 | 12389.30
 United States      |        36 |  8618.76
 Japan              |        31 |  7287.91
```

### 7. Clientes que pagaram mais do que a média do seu país

449 linhas.

```
 customer_id | first_name  |  last_name   |                country                | total  | country_avg
-------------+-------------+--------------+---------------------------------------+--------+-------------
         176 | JUNE        | CARROLL      | Algeria                               | 280.26 |      253.64
         528 | CLAUDE      | HERZOG       | Angola                                | 256.30 |      226.82
         359 | WILLIE      | MARKHAM      | Argentina                             | 293.17 |      241.67
          89 | JULIA       | FLORES       | Argentina                             | 284.22 |      241.67
         560 | JORDAN      | ARCHULETA    | Argentina                             | 273.27 |      241.67
```

### 8. Filmes mais longos de cada classificação

14 linhas.

```
 rating | film_id |       title        | length
--------+---------+--------------------+--------
 G      |     182 | CONTROL ANTHEM     |    185
 G      |     212 | DARN FORRESTER     |    185
 G      |     609 | MUSCLE BRIGHT      |    185
 PG     |     991 | WORST BANGER       |    185
 PG-13  |     141 | CHICAGO NORTH      |    185
```

### 9. Clientes sem alugueres a partir de 2026-04-01

49 linhas.

```
 customer_id | first_name |  last_name
-------------+------------+-------------
           9 | MARGARET   | MOORE
          13 | KAREN      | JACKSON
          21 | MICHELLE   | CLARK
          46 | CATHERINE  | CAMPBELL
          52 | JULIE      | SANCHEZ
```

### 10. Média de dias fora por categoria

16 linhas.

```
  category   | avg_days
-------------+----------
 Sci-Fi      |     5.30
 Music       |     5.27
 Sports      |     5.26
 Drama       |     5.18
 Children    |     5.17
```
