# Exercício 12: ORM II, migrations, transactions and API

## Enunciado

Folder: `exercises/12-api/exercise/`

**Goal.** Evolve an existing schema with reversible migrations and expose a transactional API that stays correct under concurrent requests.

**Starting point.** A fresh copy of Pagila and a uv project:

```bash
./scripts/create-db.sh ex12 --pagila --reset
uv init --bare
uv add "sqlalchemy>=2" "psycopg[binary]" alembic fastapi "uvicorn[standard]" httpx
```

Map at least `customer`, `film`, `inventory`, `rental` and `staff`. You can reuse the models of exercise 11.

**Tasks.**

1. Baseline. Initialise Alembic, create a migration `0001_baseline` with empty `upgrade` and `downgrade`, and run `alembic stamp head` on `ex12`. Configure `include_object` in `migrations/env.py` so that `--autogenerate` ignores tables you did not map. In the README, explain what `--autogenerate` would have generated without the baseline and without `include_object`, and why that is dangerous.
2. Migration `0002_loyalty_points`: add `customer.loyalty_points integer NOT NULL`, filled with the customer's number of rentals, in three steps (add as nullable, fill, set `NOT NULL`), with `server_default` 0 for new rows. `downgrade` removes the column. Expected: customer 1 has 66 points.
3. Migration `0003_one_open_rental_per_copy`: three copies (`inventory_id` 1358, 1435 and 2408) have two open rentals each. Close the older open rental of each one by setting its `return_date` to the `rental_date` of the newer one, then create the partial unique index `rental_one_open_per_copy` on `rental (inventory_id) WHERE return_date IS NULL`. `downgrade` drops the index only. In the README, explain why the data fix is not undone.
4. Show `alembic upgrade head`, `alembic downgrade base` and `alembic upgrade head` again running without errors, with `\d customer` and `\d rental` after each.
5. An API with 3 endpoints, each request with its own session:
   - `POST /rentals` with body `{"customer_id": int, "film_id": int, "store_id": int, "staff_id": int}`. In one transaction, find a copy of the film in that store with no open rental, lock it with `with_for_update(skip_locked=True)` and insert the rental with `rental_date` now. Returns `201` with `rental_id` and `inventory_id`, `404` if the customer or the film does not exist, and `409` if no copy is available. If the insert violates `rental_one_open_per_copy` (another request rented the same copy between your read and your insert), retry the whole transaction, at most 3 times, before returning `409`.
   - `POST /rentals/{rental_id}/return` sets `return_date` to now. Returns `200`, `404` if the rental does not exist, and `409` if it was already returned.
   - `GET /rentals/overdue?as_of=2026-07-31` lists open rentals whose due date (`rental_date` plus the film's `rental_duration` in days) is before `as_of`, ordered by `rental_date`. Each item has `rental_id`, `rental_date`, `due_date`, `customer` (`customer_id`, `first_name`, `last_name`) and `film` (`film_id`, `title`). It must not have an N+1. Expected on a fresh copy after the migrations: 229 items.
6. `concurrency_test.py` sends 5 simultaneous `POST /rentals` for film 7 in store 1 (customers 1 to 5, staff 6). Film 7 has exactly 2 copies in store 1, both available on a fresh copy. Expected: exactly two `201` and three `409`, with two different `inventory_id`.

**Deliverables.**

- The project: models, `migrations/`, `app/`, `concurrency_test.py`, `pyproject.toml`.
- `README.md` with the commands to run the migrations, the API and the test, the output of tasks 4 and 6, the number of SQL statements `GET /rentals/overdue` runs (from the `echo=True` log), and the explanations asked in tasks 1 and 3.

**Done when.** The migrations go up, down and up again without errors, the endpoints return the status codes above, the overdue list has 229 items in a fixed number of queries, and the concurrency test gives two `201` and three `409` every time you run it on a fresh copy.

## Challenge (opcional, em `challenge/`)

Enunciado completo em [challenge/README.md](../challenge/README.md).

## Checklist

- [x] `0001_baseline` + `alembic stamp head` + `include_object`, with explanation
- [x] `0002_loyalty_points` (customer 1 has 66 points)
- [x] `0003_one_open_rental_per_copy`, with explanation of why the data fix is not undone
- [x] upgrade / downgrade base / upgrade with `\d customer` and `\d rental`
- [x] `POST /rentals` (201/404/409, `skip_locked`, retries)
- [x] `POST /rentals/{rental_id}/return` (200/404/409)
- [x] `GET /rentals/overdue` (229 items, no N+1, number of statements)
- [x] `concurrency_test.py`: two `201` and three `409`

## Resolução

Ficheiros entregues:

- [models.py](models.py): os modelos de `customer`, `film`, `inventory`, `rental` e `staff`, com todas as colunas e índices das 5 tabelas, para o `--autogenerate` não encontrar diferenças. Descrevem o esquema em `head`: incluem `customer.loyalty_points` (0002) e o índice parcial `rental_one_open_per_copy` (0003). As chaves estrangeiras só estão declaradas entre estas 5 tabelas. As que apontam para `store`, `address` e `language` (não mapeadas) continuam na base de dados, e o `env.py` ignora-as.
- [migrations/env.py](migrations/env.py): `target_metadata = Base.metadata`, o URL vem de `models.DATABASE_URL`, e `include_object` ignora as tabelas não mapeadas e as FKs para elas.
- [migrations/versions/](migrations/versions/): [0001_baseline.py](migrations/versions/0001_baseline.py), [0002_loyalty_points.py](migrations/versions/0002_loyalty_points.py) e [0003_one_open_rental_per_copy.py](migrations/versions/0003_one_open_rental_per_copy.py).
- [app/db.py](app/db.py): o engine e a dependência `get_session`, uma sessão por pedido. Com `EX12_ECHO=1`, o engine corre com `echo=True`.
- [app/main.py](app/main.py): os 3 endpoints.
- [concurrency_test.py](concurrency_test.py): os 5 `POST /rentals` em simultâneo.
- [pyproject.toml](pyproject.toml), `uv.lock` e [alembic.ini](alembic.ini).

### Como correr

```bash
# a partir da raiz do repositório
./scripts/create-db.sh ex12 --pagila --reset
cd exercises/12-api/exercise
uv sync

# migrations
uv run alembic stamp 0001_baseline   # marca o esquema que já existe como 0001, sem correr nada
uv run alembic upgrade head
uv run alembic check                 # "No new upgrade operations detected."

# API (EX12_ECHO=1 para ver o SQL)
EX12_ECHO=1 uv run uvicorn app.main:app

# noutro terminal
curl 'http://127.0.0.1:8000/rentals/overdue?as_of=2026-07-31'
uv run python concurrency_test.py
```

O URL por omissão é `postgresql+psycopg:///ex12`: o host, o utilizador e a password vêm de `PGHOST`, `PGUSER` e `PGPASSWORD`. Para outro destino, usar `EX12_DATABASE_URL` (Alembic e API) e `EX12_API_URL` (teste).

Na tarefa 1 corri `alembic stamp head` com só a `0001_baseline` em `versions/` (tirei a 0002 e a 0003 da pasta para isso, e voltei a pô-las a seguir), e por isso `head` era a 0001. Agora, com as três migrations em `versions/`, `stamp head` marcaria a 0003 como aplicada sem correr a 0002 nem a 0003. Numa cópia nova, o comando certo é `alembic stamp 0001_baseline`.

### Tarefa 1: baseline e `include_object`

A `0001_baseline` tem `upgrade` e `downgrade` vazios. `alembic stamp` cria a tabela `alembic_version` com `0001_baseline`, sem executar nada. A partir daí, o Alembic sabe que o esquema que já existe é a revisão 0001.

Para ver o que o `--autogenerate` geraria em cada caso, comparei os modelos com a base de dados usando `alembic.autogenerate.compare_metadata`, o mesmo cálculo que `revision --autogenerate` faz, antes da 0002:

| Caso | Operações geradas |
|------|-------------------|
| `ex12` sem `include_object` | 153: **65 `drop_table`**, 79 `drop_index`, 7 `drop_constraint` (FKs), mais as 2 de baixo |
| `ex12` com `include_object` | 2: `add_column customer.loyalty_points` e `create_index rental_one_open_per_copy` |
| base vazia (sem baseline) | 18: 5 `create_table` (`customer`, `film`, `inventory`, `rental`, `staff`) e 13 `create_index` |

**Sem `include_object`.** O Alembic compara o `MetaData` com **todas** as tabelas da base de dados. Tudo o que existe na base de dados e não está nos modelos é tratado como apagado dos modelos. A migration gerada faria `op.drop_table()` das 65 tabelas que não mapeei: `actor`, `address`, `store`, `language`, `payment` e as suas 55 partições, entre outras. Também apagaria os índices delas e as 7 FKs das tabelas mapeadas para `store`, `address` e `language`. É perigoso por três razões:

- Um `alembic upgrade head` apaga as tabelas com os dados (os 51 mil pagamentos, por exemplo), e o `downgrade` gerado recria-as vazias. Os dados não voltam.
- As 2 alterações que eu queria ficam escondidas no meio de 151 que não queria, e é fácil aprovar a migration sem ler.
- Não basta ter cuidado uma vez: o problema volta em todos os `--autogenerate`.

O `include_object` devolve `False` para tabelas refletidas (`reflected`) que não têm par nos modelos (`compare_to is None`). Os índices e constraints de uma tabela só são comparados se a tabela for incluída, por isso saem com ela. A segunda regra trata das FKs para tabelas não mapeadas, que estão em tabelas incluídas.

**Sem baseline.** Sem uma revisão que represente o esquema que já existe, a base de dados não tem `alembic_version`, e o Alembic considera que está em `base`, ou seja, vazia. A primeira migration costuma gerar-se contra uma base vazia (a de um colega novo, a do CI), e dá a terceira linha da tabela: `create_table` das 5 tabelas. Isto tem dois problemas:

- Em `ex12`, `alembic upgrade head` falha logo com `DuplicateTable: relation "customer" already exists`. Para continuar, a tentação é apagar as tabelas ou fazer `stamp` à mão por cima dessa migration.
- O `downgrade` dessa migration faz `drop_table` de `customer`, `film`, `inventory`, `rental` e `staff`. `alembic downgrade base` apagava as 5 tabelas com os dados, ou falhava a meio por causa das FKs de `payment`.

Com a baseline vazia e o `stamp`, `upgrade` começa na 0002 e `downgrade base` para na 0001 sem tocar nas tabelas, como se vê na tarefa 4.

Em `head`, `alembic check` não encontra diferenças entre os modelos e a base de dados (`No new upgrade operations detected.`).

### Tarefa 2: `0002_loyalty_points`

1. `op.add_column(..., nullable=True)`: sem default, só altera o catálogo e não reescreve a tabela. As linhas existentes ficam com `NULL`.
2. `UPDATE customer c SET loyalty_points = (SELECT count(*) FROM rental r WHERE r.customer_id = c.customer_id)`.
3. `op.alter_column(..., nullable=False, server_default=sa.text("0"))`: o `NOT NULL` só é aceite porque o passo 2 não deixou nenhum `NULL`. O default `0` serve para os clientes inseridos daqui em diante.

O `downgrade` faz `op.drop_column`. Depois do `upgrade`, o cliente 1 tem 66 pontos (`SELECT loyalty_points FROM customer WHERE customer_id = 1` → `66`).

Nota: o `UPDATE` dispara o trigger `last_updated`, por isso o `last_update` dos 999 clientes passa para a hora da migration.

### Tarefa 3: `0003_one_open_rental_per_copy`

| `inventory_id` | Aluguer mais antigo | `return_date` depois da 0003 | Aluguer em aberto |
|---:|---|---|---|
| 1358 | 12130, 2022-02-14 15:16:03 | 2026-07-20 13:33:38.674648 | 87353 |
| 1435 | 12792, 2022-02-14 15:16:03 | 2026-07-19 12:44:26.675207 | 87318 |
| 2408 | 13295, 2022-02-14 15:16:03 | 2026-07-27 16:12:39.377683 | 87514 |

O `UPDATE` não usa os três ids do enunciado. Usa `lead(rental_date) OVER (PARTITION BY inventory_id ORDER BY rental_date, rental_id)` sobre os alugueres em aberto, e fecha cada um com a data do aluguer em aberto seguinte da mesma cópia. Também funcionaria se uma cópia tivesse três alugueres em aberto, e numa base de dados diferente desta. Só depois cria o índice único parcial `rental_one_open_per_copy ON rental (inventory_id) WHERE return_date IS NULL`. O `downgrade` faz apenas `op.drop_index`.

**Porque é que o `downgrade` não desfaz a correção dos dados:**

- **Os dados antigos estavam errados.** Dois alugueres em aberto da mesma cópia física é impossível: a cópia voltou à loja quando foi alugada outra vez. Repor `return_date = NULL` não restaura um estado válido. Volta a criar a inconsistência que a migration corrigiu.
- **O código antigo não precisa disso.** O `downgrade` existe para o esquema voltar a ser o que o código da versão anterior espera. Esse código funciona com alugueres fechados (é o caso normal), e só deixa de ter o índice a protegê-lo.
- **Não se sabe de forma segura o que desfazer.** O `downgrade` teria de reabrir exatamente as linhas que o `upgrade` fechou. Para isso precisava de guardar os ids algures, ou de os adivinhar pela condição `return_date = rental_date do aluguer seguinte`. Essa condição apanha também alugueres devolvidos legitimamente nesse instante. Além disso, entre o `upgrade` e o `downgrade` a aplicação pode ter mexido nessas linhas ou nessas cópias. Reabrir às cegas um aluguer de uma cópia entretanto alugada outra vez estragava dados bons.
- **O `upgrade` seguinte não precisa disso.** Depois de `downgrade base` e `upgrade head`, o `UPDATE` não encontra cópias com dois alugueres em aberto e não altera nada. A migration é idempotente nos dados, e o índice volta a ser criado sem erros (tarefa 4).

Em geral, um `downgrade` desfaz alterações de esquema, mas não desfaz correções de dados que apagam informação errada. Se fosse preciso voltar mesmo ao estado anterior, o caminho era um backup.

### Tarefa 4: `upgrade head`, `downgrade base`, `upgrade head`

Numa cópia nova de Pagila. Omiti as secções `Referenced by` do `\d` (são as FKs das partições de `payment`, iguais nos três passos).

```
$ uv run alembic stamp head   # só com 0001_baseline em versions/
INFO  [alembic.runtime.migration] Running stamp_revision  -> 0001_baseline

$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade 0001_baseline -> 0002_loyalty_points, customer.loyalty_points: one point per rental
INFO  [alembic.runtime.migration] Running upgrade 0002_loyalty_points -> 0003_one_open_rental_per_copy, rental_one_open_per_copy: at most one open rental per copy
$ psql -d ex12 -c '\d customer' -c '\d rental'
                                             Table "public.customer"
     Column     |           Type           | Collation | Nullable |                    Default
----------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id    | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id       | integer                  |           | not null |
 first_name     | text                     |           | not null |
 last_name      | text                     |           | not null |
 email          | text                     |           |          |
 address_id     | integer                  |           | not null |
 activebool     | boolean                  |           | not null | true
 create_date    | date                     |           | not null | CURRENT_DATE
 last_update    | timestamp with time zone |           |          | now()
 active         | integer                  |           |          |
 uuid           | uuid                     |           | not null | uuidv7()
 loyalty_points | integer                  |           | not null | 0
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)
Foreign-key constraints:
    "customer_address_id_fkey" FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "customer_store_id_fkey" FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE ON DELETE RESTRICT
Referenced by: (omitido)
Triggers:
    last_updated BEFORE UPDATE ON customer FOR EACH ROW EXECUTE FUNCTION last_updated()

                                           Table "public.rental"
    Column    |           Type           | Collation | Nullable |                  Default
--------------+--------------------------+-----------+----------+-------------------------------------------
 rental_id    | integer                  |           | not null | nextval('rental_rental_id_seq'::regclass)
 rental_date  | timestamp with time zone |           | not null |
 inventory_id | integer                  |           | not null |
 customer_id  | integer                  |           | not null |
 return_date  | timestamp with time zone |           |          |
 staff_id     | integer                  |           | not null |
 last_update  | timestamp with time zone |           | not null | now()
 uuid         | uuid                     |           | not null | uuidv7()
Indexes:
    "rental_pkey" PRIMARY KEY, btree (rental_id)
    "idx_fk_inventory_id" btree (inventory_id)
    "idx_unq_rental_rental_date_inventory_id_customer_id" UNIQUE, btree (rental_date, inventory_id, customer_id)
    "rental_one_open_per_copy" UNIQUE, btree (inventory_id) WHERE return_date IS NULL
    "rental_uuid_key" UNIQUE, btree (uuid)
Foreign-key constraints:
    "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_inventory_id_fkey" FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_staff_id_fkey" FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT
Referenced by: (omitido)
Triggers:
    last_updated BEFORE UPDATE ON rental FOR EACH ROW EXECUTE FUNCTION last_updated()

$ uv run alembic downgrade base
INFO  [alembic.runtime.migration] Running downgrade 0003_one_open_rental_per_copy -> 0002_loyalty_points, rental_one_open_per_copy: at most one open rental per copy
INFO  [alembic.runtime.migration] Running downgrade 0002_loyalty_points -> 0001_baseline, customer.loyalty_points: one point per rental
INFO  [alembic.runtime.migration] Running downgrade 0001_baseline -> , baseline: the Pagila schema as it already exists in ex12
$ psql -d ex12 -c '\d customer' -c '\d rental'
                                            Table "public.customer"
   Column    |           Type           | Collation | Nullable |                    Default
-------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id    | integer                  |           | not null |
 first_name  | text                     |           | not null |
 last_name   | text                     |           | not null |
 email       | text                     |           |          |
 address_id  | integer                  |           | not null |
 activebool  | boolean                  |           | not null | true
 create_date | date                     |           | not null | CURRENT_DATE
 last_update | timestamp with time zone |           |          | now()
 active      | integer                  |           |          |
 uuid        | uuid                     |           | not null | uuidv7()
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)
Foreign-key constraints:
    "customer_address_id_fkey" FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "customer_store_id_fkey" FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE ON DELETE RESTRICT
Referenced by: (omitido)
Triggers:
    last_updated BEFORE UPDATE ON customer FOR EACH ROW EXECUTE FUNCTION last_updated()

                                           Table "public.rental"
    Column    |           Type           | Collation | Nullable |                  Default
--------------+--------------------------+-----------+----------+-------------------------------------------
 rental_id    | integer                  |           | not null | nextval('rental_rental_id_seq'::regclass)
 rental_date  | timestamp with time zone |           | not null |
 inventory_id | integer                  |           | not null |
 customer_id  | integer                  |           | not null |
 return_date  | timestamp with time zone |           |          |
 staff_id     | integer                  |           | not null |
 last_update  | timestamp with time zone |           | not null | now()
 uuid         | uuid                     |           | not null | uuidv7()
Indexes:
    "rental_pkey" PRIMARY KEY, btree (rental_id)
    "idx_fk_inventory_id" btree (inventory_id)
    "idx_unq_rental_rental_date_inventory_id_customer_id" UNIQUE, btree (rental_date, inventory_id, customer_id)
    "rental_uuid_key" UNIQUE, btree (uuid)
Foreign-key constraints:
    "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_inventory_id_fkey" FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_staff_id_fkey" FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT
Referenced by: (omitido)
Triggers:
    last_updated BEFORE UPDATE ON rental FOR EACH ROW EXECUTE FUNCTION last_updated()

$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_baseline, baseline: the Pagila schema as it already exists in ex12
INFO  [alembic.runtime.migration] Running upgrade 0001_baseline -> 0002_loyalty_points, customer.loyalty_points: one point per rental
INFO  [alembic.runtime.migration] Running upgrade 0002_loyalty_points -> 0003_one_open_rental_per_copy, rental_one_open_per_copy: at most one open rental per copy
$ psql -d ex12 -c '\d customer' -c '\d rental'
                                             Table "public.customer"
     Column     |           Type           | Collation | Nullable |                    Default
----------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id    | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id       | integer                  |           | not null |
 first_name     | text                     |           | not null |
 last_name      | text                     |           | not null |
 email          | text                     |           |          |
 address_id     | integer                  |           | not null |
 activebool     | boolean                  |           | not null | true
 create_date    | date                     |           | not null | CURRENT_DATE
 last_update    | timestamp with time zone |           |          | now()
 active         | integer                  |           |          |
 uuid           | uuid                     |           | not null | uuidv7()
 loyalty_points | integer                  |           | not null | 0
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)
Foreign-key constraints:
    "customer_address_id_fkey" FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "customer_store_id_fkey" FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE ON DELETE RESTRICT
Referenced by: (omitido)
Triggers:
    last_updated BEFORE UPDATE ON customer FOR EACH ROW EXECUTE FUNCTION last_updated()

                                           Table "public.rental"
    Column    |           Type           | Collation | Nullable |                  Default
--------------+--------------------------+-----------+----------+-------------------------------------------
 rental_id    | integer                  |           | not null | nextval('rental_rental_id_seq'::regclass)
 rental_date  | timestamp with time zone |           | not null |
 inventory_id | integer                  |           | not null |
 customer_id  | integer                  |           | not null |
 return_date  | timestamp with time zone |           |          |
 staff_id     | integer                  |           | not null |
 last_update  | timestamp with time zone |           | not null | now()
 uuid         | uuid                     |           | not null | uuidv7()
Indexes:
    "rental_pkey" PRIMARY KEY, btree (rental_id)
    "idx_fk_inventory_id" btree (inventory_id)
    "idx_unq_rental_rental_date_inventory_id_customer_id" UNIQUE, btree (rental_date, inventory_id, customer_id)
    "rental_one_open_per_copy" UNIQUE, btree (inventory_id) WHERE return_date IS NULL
    "rental_uuid_key" UNIQUE, btree (uuid)
Foreign-key constraints:
    "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_inventory_id_fkey" FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_staff_id_fkey" FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT
Referenced by: (omitido)
Triggers:
    last_updated BEFORE UPDATE ON rental FOR EACH ROW EXECUTE FUNCTION last_updated()
```

As colunas de `customer` passam de 11 para 12 e voltam a 11, e o índice `rental_one_open_per_copy` aparece, desaparece e volta, sem erros. Depois do segundo `upgrade head`, o cliente 1 continua com 66 pontos.

### Tarefa 5: API

Cada pedido tem a sua `Session` (dependência `get_session`), e cada transação é um bloco `with session.begin():`. Um `HTTPException` levantado dentro do bloco faz `ROLLBACK`.

**`POST /rentals`**

```sql
-- SQL gerado (echo=True)
SELECT inventory.inventory_id
FROM inventory
WHERE inventory.film_id = %(film_id_1)s::INTEGER AND inventory.store_id = %(store_id_1)s::INTEGER
  AND NOT (EXISTS (SELECT * FROM rental
                   WHERE rental.inventory_id = inventory.inventory_id AND rental.return_date IS NULL))
ORDER BY inventory.inventory_id
LIMIT %(param_1)s::INTEGER FOR UPDATE OF inventory SKIP LOCKED

INSERT INTO rental (rental_date, inventory_id, customer_id, return_date, staff_id)
VALUES (now(), %(inventory_id)s::INTEGER, ...) RETURNING rental.rental_id, rental.rental_date, ...
```

- `404` se `session.get(Customer, ...)` ou `session.get(Film, ...)` devolve `None`. Também devolvo `404` para um `staff_id` que não existe, que de outra forma seria uma violação de FK e um `500`.
- `FOR UPDATE OF inventory SKIP LOCKED` tranca a cópia escolhida. Um pedido concorrente salta-a em vez de esperar e fica com outra cópia, ou com nenhuma, e devolve `409`.
- Se o `INSERT` falha com `IntegrityError` e `e.orig.diag.constraint_name == "rental_one_open_per_copy"`, a transação é desfeita e repetida do início, até `MAX_RETRIES = 3` vezes depois da primeira tentativa. Se esgotar as tentativas, devolve `409`. Outras `IntegrityError` não são repetidas.

A janela para o retry é estreita, e no teste da tarefa 6 nunca aconteceu. O `INSERT` em `rental` verifica a FK para `inventory`, e essa verificação tranca a linha da cópia com `FOR KEY SHARE` até ao fim da transação. `FOR KEY SHARE` entra em conflito com `FOR UPDATE`, por isso enquanto o pedido A não faz commit, o pedido B salta a cópia por causa do `SKIP LOCKED`. O retry só é preciso quando A faz commit (e liberta a linha) depois de o `SELECT` de B ter tirado o snapshot e antes de B trancar a linha. Aí B não vê o aluguer de A, tranca a cópia livre e falha no índice. Para confirmar que o retry funciona, forcei esse caso: outra transação inseriu um aluguer da cópia 33 com `session_replication_role = replica` (sem o trigger da FK, e portanto sem `FOR KEY SHARE`) e só fez commit 1 segundo depois. No log da API:

```
INSERT INTO rental (rental_date, inventory_id, ...) ...        -- espera pelo índice único
ROLLBACK
INFO:     POST /rentals: copy taken by another request, attempt 1
ROLLBACK                                                       -- 2.ª tentativa: nenhuma cópia livre
INFO:     127.0.0.1:41500 - "POST /rentals HTTP/1.1" 409 Conflict
```

**`POST /rentals/{rental_id}/return`**: `SELECT ... FOR UPDATE` do aluguer, `404` se não existe, `409` se `return_date` já está preenchida, senão `return_date = now()`. Com o `FOR UPDATE`, duas devoluções simultâneas do mesmo aluguer ficam em fila, e a segunda vê a data escrita pela primeira.

Códigos de estado verificados com `curl`:

| Pedido | Resultado |
|--------|-----------|
| `POST /rentals` com `customer_id` 99999 | `404 {"detail":"customer not found"}` |
| `POST /rentals` com `film_id` 99999 | `404 {"detail":"film not found"}` |
| `POST /rentals` do filme 7 na loja 1 com as duas cópias alugadas | `409 {"detail":"no copy of this film is available in this store"}` |
| `POST /rentals/87560/return` | `200 {"rental_id":87560,"return_date":"2026-10-30T21:39:09.368022Z"}` |
| `POST /rentals/87560/return` outra vez | `409 {"detail":"rental already returned"}` |
| `POST /rentals/99999999/return` | `404 {"detail":"rental not found"}` |
| `POST /rentals` do filme 7 na loja 1 a seguir à devolução | `201 {"rental_id":87562,"inventory_id":32}` |

**`GET /rentals/overdue?as_of=2026-07-31`**: **229 itens**, ordenados por `rental_date` (e `rental_id`, para desempatar os muitos alugueres de 2022-02-14 15:16:03). O primeiro e o último:

```json
{"rental_id": 11496, "rental_date": "2022-02-14T15:16:03Z", "due_date": "2022-02-19T15:16:03Z",
 "customer": {"customer_id": 155, "first_name": "GAIL", "last_name": "KNIGHT"},
 "film": {"film_id": 445, "title": "HYDE DOCTOR"}}
{"rental_id": 87512, "rental_date": "2026-07-27T21:22:13.614736Z", "due_date": "2026-07-30T21:22:13.614736Z",
 "customer": {"customer_id": 511, "first_name": "CHESTER", "last_name": "BENNER"},
 "film": {"film_id": 606, "title": "MUMMY CREATURES"}}
```

O log com `echo=True` de um pedido mostra **1 statement SQL**, um único `SELECT`, entre o `BEGIN (implicit)` e o `ROLLBACK` da sessão:

```
INFO sqlalchemy.engine.Engine BEGIN (implicit)
INFO sqlalchemy.engine.Engine SELECT customer.customer_id, customer.store_id, customer.first_name, ..., film.film_id, film.title, ...,
       inventory.inventory_id, ..., rental.rental_id, rental.rental_date, ...,
       rental.rental_date + film.rental_duration * interval '1 day' AS due_date
FROM rental JOIN customer ON customer.customer_id = rental.customer_id
     JOIN inventory ON inventory.inventory_id = rental.inventory_id
     JOIN film ON film.film_id = inventory.film_id
WHERE rental.return_date IS NULL AND rental.rental_date + film.rental_duration * interval '1 day' < %(param_1)s::DATE
ORDER BY rental.rental_date, rental.rental_id
INFO sqlalchemy.engine.Engine [generated in 0.00008s] {'param_1': datetime.date(2026, 7, 31)}
INFO sqlalchemy.engine.Engine ROLLBACK
```

Os joins com `customer`, `inventory` e `film` já são precisos para o filtro, por causa do `rental_duration`. `contains_eager(Rental.customer)` e `contains_eager(Rental.inventory).contains_eager(Inventory.film)` dizem ao ORM para preencher as relações a partir desses joins. Sem essas opções, a mesma lista faz **628 statements**: 1 da lista mais os lazy loads de `rental.customer`, `rental.inventory` e `inventory.film`, menos os objetos que já estavam no identity map. O primeiro pedido de cada processo faz ainda 3 queries de inicialização do dialeto (`select pg_catalog.version()`, `select current_schema()`, `show standard_conforming_strings`), uma vez por engine e não por pedido.

`as_of` é uma `date`. Na comparação com `timestamptz`, o PostgreSQL converte-a para a meia-noite no fuso da sessão (UTC). Um aluguer com data de devolução prevista para 2026-07-31 às 10h ainda não está em atraso.

### Tarefa 6: `concurrency_test.py`

Com a API a correr, numa cópia nova depois das migrations:

```
$ uv run python concurrency_test.py
customer 1: 409 {'detail': 'no copy of this film is available in this store'}
customer 2: 409 {'detail': 'no copy of this film is available in this store'}
customer 3: 201 {'rental_id': 87561, 'inventory_id': 33}
customer 4: 201 {'rental_id': 87560, 'inventory_id': 32}
customer 5: 409 {'detail': 'no copy of this film is available in this store'}

201: 2, 409: 3, inventory_id of the 201s: [32, 33]
OK
```

Repeti o ciclo `create-db.sh --reset`, `stamp`, `upgrade head`, arrancar a API e correr o teste 7 vezes seguidas. Deu sempre dois `201` (cópias 32 e 33) e três `409`. Os clientes que ficam com as cópias mudam de corrida para corrida, porque dependem da ordem em que os pedidos chegam. Numa segunda corrida sobre a mesma base de dados, os 5 pedidos dão `409`, porque as duas cópias continuam alugadas.
