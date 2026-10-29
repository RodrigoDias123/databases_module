# Exercício 04: CRUD, upsert and bulk data

Ficheiros entregues:

- `README.md`: este ficheiro, com o output de cada operação.
- [queries.sql](queries.sql): as 12 operações, numeradas de `-- 1.` a `-- 12.`

## Como correr

A partir da root do repositório, numa cópia limpa da Pagila:

```bash
./scripts/create-db.sh ex04 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex04 -v ON_ERROR_STOP=1 < exercises/04-crud/exercise/queries.sql
```

O script corre de uma ponta à outra sem erros. Tem de correr uma só vez: a operação 7 só dá `actor_id` 201 e a 9 só dá `awards` 2 numa cópia limpa.

## Resumo

| # | Operação | Esperado | Obtido |
|---|----------|----------|--------|
| 1 | Filmes `PG-13` com mais de 120 min, por título | 118 linhas, `APOLLO TEEN` … `WRONG BEHAVIOR` | ✅ igual |
| 2 | Atores com `son` no apelido (`ILIKE`) | 9 linhas | ✅ 9 |
| 3 | Alugueres por devolver (`return_date IS NULL`) | 241 linhas | ✅ 241 |
| 4 | `rental_duration` distintos | 5 linhas, 3 a 7 | ✅ igual |
| 5 | 3.ª página de filmes por título (`LIMIT 10 OFFSET 20`) | 10 linhas, `AMERICAN CIRCUS` … `ANYTHING SAVANNAH` | ✅ igual |
| 6 | Alugueres em janeiro de 2026, com `BETWEEN` e com intervalo semiaberto | 746 e 781 | ✅ 746 e 781 |
| 7 | `INSERT` de `ADA LOVELACE` com `RETURNING` | `actor_id` 201 | ✅ 201 |
| 8 | `rental_rate + 0.50` nos `NC-17` com menos de 60 min, numa transação | 21 no `SELECT` e no `UPDATE` | ✅ 21 e 21 |
| 9 | Upsert de um prémio para o ator 1, duas vezes | `awards` = 2 | ✅ 1, depois 2 |
| 10 | Ator 2 com 5 prémios, `ON CONFLICT DO NOTHING`, duas vezes | 1 linha, depois 0 | ✅ `INSERT 0 1`, `INSERT 0 0` |
| 11 | 3 pagamentos de teste num só `INSERT` | 3 linhas | ✅ 3 |
| 12 | Apagar os 3 pagamentos, numa transação | 3 no `SELECT` e no `DELETE` | ✅ 3 e 3 |

## 6. Porque é que `BETWEEN` dá 746 e o intervalo semiaberto dá 781

`rental_date` é `timestamptz`. Num `BETWEEN`, `'2026-01-31'` é convertido para `2026-01-31 00:00:00`, por isso a condição só apanha o dia 31 até à meia-noite em ponto e deixa de fora os 35 alugueres desse dia. A forma correta é a segunda, `>= '2026-01-01' AND < '2026-02-01'`. O intervalo semiaberto cobre o mês inteiro, seja qual for a precisão da hora, e não conta duas vezes um aluguer feito à meia-noite de 1 de fevereiro.

## Output de cada operação

### 1. Filmes PG-13 com mais de 120 minutos

```
 film_id |            title            | length
---------+-----------------------------+--------
      33 | APOLLO TEEN                 |    153
      35 | ARACHNOPHOBIA ROLLERCOASTER |    147
...
     990 | WORLD LEATHERNECKS          |    171
     993 | WRONG BEHAVIOR              |    178
(118 rows)
```

### 2. Atores com `son` no apelido

```
 actor_id | first_name | last_name
----------+------------+-----------
      154 | MERYL      | GIBSON
       65 | ANGELA     | HUDSON
      146 | ALBERT     | JOHANSSON
        8 | MATTHEW    | JOHANSSON
       64 | RAY        | JOHANSSON
       61 | CHRISTIAN  | NEESON
       62 | JAYNE      | NEESON
        6 | BETTE      | NICHOLSON
      168 | WILL       | WILSON
(9 rows)
```

### 3. Alugueres por devolver

```
 rental_id |          rental_date          | inventory_id | customer_id
-----------+-------------------------------+--------------+-------------
     11496 | 2022-02-14 15:16:03+00        |         2047 |         155
     11541 | 2022-02-14 15:16:03+00        |         2026 |         335
...
     87527 | 2026-07-27 09:29:05.894069+00 |         2772 |           8
     87534 | 2026-07-27 04:40:26.294744+00 |          324 |         235
(241 rows)
```

### 4. Valores distintos de `rental_duration`

```
 rental_duration
-----------------
               3
               4
               5
               6
               7
(5 rows)
```

### 5. Terceira página de filmes

```
 film_id |        title
---------+----------------------
      21 | AMERICAN CIRCUS
      22 | AMISTAD MIDSUMMER
      23 | ANACONDA CONFESSIONS
      24 | ANALYZE HOOSIERS
      25 | ANGELS LIFE
      26 | ANNIE IDENTITY
      27 | ANONYMOUS HUMAN
      28 | ANTHEM LUKE
      29 | ANTITRUST TOMATOES
      30 | ANYTHING SAVANNAH
(10 rows)
```

### 6. Alugueres em janeiro de 2026

```
 with_between
--------------
          746
(1 row)

 with_half_open
----------------
            781
(1 row)
```

### 7. Inserir `ADA LOVELACE`

```
 actor_id
----------
      201
(1 row)

INSERT 0 1
```

### 8. Aumentar o `rental_rate` dos filmes NC-17 curtos

```
BEGIN
 count
-------
    21
(1 row)

 film_id |        title        | rental_rate
---------+---------------------+-------------
       3 | ADAPTATION HOLES    |        3.49
      15 | ALIEN CENTER        |        3.49
      66 | BENEATH RUSH        |        1.49
     110 | CABIN FLASH         |        1.49
     111 | CADDYSHACK JEDI     |        1.49
     187 | CRANES RESERVOIR    |        3.49
     205 | DANCES NONE         |        1.49
     243 | DOORS PRESIDENT     |        5.49
     386 | GUMP DATE           |        5.49
     392 | HALL CASSIDY        |        5.49
     398 | HANOVER GALAXY      |        5.49
     411 | HEAVENLY GUN        |        5.49
     634 | ODDS BOOGIE         |        1.49
     799 | SIMON NORTH         |        1.49
     824 | SPARTACUS CHEAPER   |        5.49
     845 | STEPMOM DREAM       |        5.49
     849 | STORM HAPPINESS     |        1.49
     866 | SUNSET RACER        |        1.49
     970 | WESTWARD SEABISCUIT |        1.49
     981 | WOLVES DESIRE       |        1.49
    1000 | ZORRO ARK           |        5.49
(21 rows)

UPDATE 21
COMMIT
```

O `count` dá 21, igual ao número de linhas do `UPDATE`, por isso faz-se `COMMIT`.

### 9. Upsert de prémios para o ator 1

```
CREATE TABLE
 actor_id | awards
----------+--------
        1 |      1
(1 row)

INSERT 0 1
 actor_id | awards
----------+--------
        1 |      2
(1 row)

INSERT 0 1
```

A primeira execução insere a linha com 1. Na segunda há conflito em `actor_id`, e o `DO UPDATE` soma 1 ao valor que já existe (`actor_award.awards + 1`).

### 10. Ator 2 com `ON CONFLICT DO NOTHING`

```
INSERT 0 1
INSERT 0 0
```

### 11. Inserir 3 pagamentos de teste

```
 payment_id
------------
     102095
     102096
     102097
(3 rows)

INSERT 0 3
```

### 12. Apagar os pagamentos de teste

```
BEGIN
 count
-------
     3
(1 row)

 payment_id
------------
     102095
     102096
     102097
(3 rows)

DELETE 3
COMMIT
```

O `SELECT count(*)` usa exatamente o mesmo `WHERE` do `DELETE` e dá 3. O `DELETE` devolve os 3 `payment_id` da operação 11.
