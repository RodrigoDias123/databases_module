# Challenge 04: CRUD, upsert and bulk data

Obrigatório.

## Enunciado

Folder: `exercises/04-crud/challenge/`

**Goal.** Generate a large, valid and reproducible data set quickly.

**Starting point.** Two fresh copies of Pagila and a uv project:

```bash
./scripts/create-db.sh ch04_a --pagila --reset
./scripts/create-db.sh ch04_b --pagila --reset
uv init --bare
uv add faker "psycopg[binary]"
```

**Tasks.**

1. Write `seed.py`, which adds 1,000,000 rows to `rental` using `COPY`. The database name is a command-line argument.
   - Use explicit `rental_id` values from 100,001 to 1,100,000, so that both runs produce the same keys. After the load, move the sequence past the last ID with `setval`.
   - Every `inventory_id`, `customer_id` and `staff_id` must exist in Pagila.
   - `rental_date` is between `2022-01-01` and `2026-07-31`; `return_date` is either `NULL` or later than `rental_date`.
   - Respect the existing unique index on `(rental_date, inventory_id, customer_id)`.
   - Overlapping rentals of the same copy are allowed in this challenge.
   - Use a fixed random seed.
2. Run it on `ch04_a` and on `ch04_b` and time each run.
3. Prove that both databases have identical new rows by comparing this checksum on both:

   ```sql
   SELECT md5(string_agg(concat_ws('|', rental_id, rental_date, inventory_id, customer_id, return_date, staff_id), ',' ORDER BY rental_id))
   FROM rental WHERE rental_id > 100000;
   ```

4. Make the script idempotent: running it a second time on `ch04_a` must not add or change any row. Prove it with the row count and the checksum before and after.

**Deliverables.**

- `seed.py`, `pyproject.toml`.
- `README.md` with the run commands, the measured times, both checksums and the idempotency proof.

**Done when.** Each load adds exactly 1,000,000 valid rows, takes under 30 seconds on your machine (report the time), the two checksums are equal, and the second run on the same database changes nothing.


## Resposta

Ficheiros: [seed.py](seed.py) e [pyproject.toml](pyproject.toml). Esta pasta já é um projeto uv (membro do workspace da root), por isso não é preciso `uv init`. Dependências: `faker` e `psycopg[binary]`, como no enunciado.

### Como correr

A partir da root do repositório:

```bash
./scripts/create-db.sh ch04_a --pagila --reset
./scripts/create-db.sh ch04_b --pagila --reset
cd exercises/04-crud/challenge
uv run seed.py ch04_a
uv run seed.py ch04_b
uv run seed.py ch04_a   # segunda vez: não muda nada
```

O nome da base de dados é o único argumento. O host, o utilizador e a password vêm de `DATABASE_URL` ou das variáveis `PG*`. No dev container já estão definidas. Fora dele, usa `uv run --env-file ../../../.env seed.py ch04_a`. O nome da base dado como argumento substitui o que vier no URL.

### Tempos, checksums e idempotência

Em cada execução, o script mostra o número de linhas com `rental_id > 100000` e o checksum do enunciado, antes e depois:

```
ch04_a: before: 0 rows, md5 None
ch04_a: inserted 1,000,000 rentals
ch04_a: after:  1000000 rows, md5 871294888f42d7528ef54093b707f4eb
ch04_a: 23.3 s
ch04_b: before: 0 rows, md5 None
ch04_b: inserted 1,000,000 rentals
ch04_b: after:  1000000 rows, md5 871294888f42d7528ef54093b707f4eb
ch04_b: 22.6 s
ch04_a: before: 1000000 rows, md5 871294888f42d7528ef54093b707f4eb
ch04_a: the 1,000,000 rentals are already there, nothing to do
ch04_a: after:  1000000 rows, md5 871294888f42d7528ef54093b707f4eb
ch04_a: 1.0 s
```

| Execução | Tempo | Linhas antes → depois | Checksum depois |
|----------|-------|-----------------------|-----------------|
| `ch04_a` | 23,3 s | 0 → 1 000 000 | `871294888f42d7528ef54093b707f4eb` |
| `ch04_b` | 22,6 s | 0 → 1 000 000 | `871294888f42d7528ef54093b707f4eb` |
| `ch04_a` (2.ª vez) | 1,0 s | 1 000 000 → 1 000 000 | `871294888f42d7528ef54093b707f4eb` (igual ao de antes) |

Os tempos incluem gerar as linhas em Python, o `COPY`, a verificação das 3 FK e dos índices, o `setval` e os dois checksums.

O checksum do enunciado, corrido no `psql` em cada base, dá o mesmo valor nas duas:

```
$ docker compose exec -T postgres psql -U postgres -d ch04_a -c "SELECT md5(...) FROM rental WHERE rental_id > 100000;"
               md5
----------------------------------
 871294888f42d7528ef54093b707f4eb
(1 row)

$ docker compose exec -T postgres psql -U postgres -d ch04_b -c "SELECT md5(...) FROM rental WHERE rental_id > 100000;"
               md5
----------------------------------
 871294888f42d7528ef54093b707f4eb
(1 row)
```

### Todas as linhas são válidas

Verificação em `ch04_a`:

```sql
SELECT count(*) AS novas,
  min(rental_id) AS min_id, max(rental_id) AS max_id,
  min(rental_date) AS min_data, max(rental_date) AS max_data,
  count(*) FILTER (WHERE return_date IS NULL) AS por_devolver,
  count(*) FILTER (WHERE return_date <= rental_date) AS return_invalido,
  count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM inventory i WHERE i.inventory_id = r.inventory_id)) AS inventory_invalido,
  count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM customer c WHERE c.customer_id = r.customer_id)) AS customer_invalido,
  count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM staff s WHERE s.staff_id = r.staff_id)) AS staff_invalido
FROM rental r WHERE rental_id > 100000;

SELECT last_value FROM rental_rental_id_seq;
```

```
  novas  | min_id | max_id  |           min_data            |           max_data            | por_devolver | return_invalido | inventory_invalido | customer_invalido | staff_invalido
---------+--------+---------+-------------------------------+-------------------------------+--------------+-----------------+--------------------+-------------------+----------------
 1000000 | 100001 | 1100000 | 2022-01-01 00:01:31.438032+00 | 2026-07-25 15:59:01.643194+00 |        19933 |               0 |                  0 |                 0 |              0
(1 row)

 last_value
------------
    1100000
(1 row)
```

Como o script garante cada regra:

- **IDs explícitos**: `rental_id` vai de 100 001 a 1 100 000. No fim, `setval('rental_rental_id_seq', max(rental_id))` passa a sequence para depois do último ID, e o próximo `INSERT` sem ID recebe 1 100 001.
- **FKs**: `inventory_id`, `customer_id` e `staff_id` são escolhidos das listas de IDs lidas da própria base, com `ORDER BY`. As FK da tabela também o garantem: se um ID não existisse, o `COPY` falhava inteiro.
- **Datas**: a linha `i` tem o seu próprio intervalo de 144 segundos a partir de `2022-01-01`, e a `rental_date` é um instante aleatório (ao microssegundo) dentro desse intervalo, gerado com `fake.date_time_between`. 1 000 000 × 144 s acaba a 2026-07-25, antes de `2026-07-31`. Cerca de 2% das linhas ficam com `return_date` a `NULL` (por devolver, com `fake.boolean(chance_of_getting_true=2)`). As outras ficam entre 1 hora e 10 dias depois da `rental_date` (`fake.date_time_between`).
- **Índice único `(rental_date, inventory_id, customer_id)`**: entre as linhas novas, cada `rental_date` é maior do que a anterior, por isso nunca se repete. Os alugueres originais da Pagila estão no mesmo período, por isso o script lê as suas chaves para um `set` e, se uma linha nova coincidir com uma delas, volta a sortear o exemplar e o cliente. Como o sorteio usa o mesmo gerador, o resultado é igual em todas as execuções.
- **Seed fixa**: `Faker.seed(42)`, como no tutorial. Todos os valores aleatórios vêm do Faker, por isso as escolhas são sempre as mesmas. As colunas que o PostgreSQL preencheria de forma diferente em cada execução também são definidas pelo script: `uuid` vem de `fake.uuid4()` (em vez de `uuidv7()`) e `last_update` é uma data fixa (em vez de `now()`).

### Porque é idempotente

Tudo corre numa só transação. Antes de inserir, o script conta as linhas no intervalo de IDs do seed:

- 0 linhas: insere as 1 000 000;
- 1 000 000 linhas: não faz nada;
- outro número: para com erro, porque alguém mexeu nos dados à mão.

Como a transação é tudo ou nada, um seed interrompido a meio não deixa linhas para trás. O `LOCK TABLE rental IN SHARE ROW EXCLUSIVE MODE` impede que duas execuções ao mesmo tempo vejam as duas 0 linhas e insiram as duas: a segunda espera pela primeira e depois encontra os dados. O `setval` volta a correr na segunda vez, mas não muda nenhuma linha.

### Menos de 30 segundos com `COPY`

As linhas são enviadas em blocos de 50 000 num único `COPY ... FROM STDIN`, e o servidor recebe-as em stream num só comando. Com um `INSERT` por linha, cada uma das 1 000 000 linhas seria uma ida e volta ao servidor.

A maior parte do tempo é gasta no Faker a gerar as linhas. A primeira versão usava `fake.random_element(lista)` para escolher o exemplar, o cliente e o funcionário, e demorava 33 s. Medido com `timeit`, `random_element` custa cerca de 6,7 s por milhão de chamadas e `fake.random_int` cerca de 0,75 s. Por isso o script escolhe um índice com `fake.random_int(0, len(lista) - 1)`. O resultado é o mesmo (o checksum não mudou) e o tempo desce para 23 s.
