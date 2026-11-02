# Challenge 12: ORM II, migrations, transactions and API

Opcional.

## Enunciado

Folder: `exercises/12-api/challenge/`

**Goal.** Rename a column used by a running API without downtime, using the expand and contract pattern.

**Starting point.** The project of the exercise above. The column to rename is `customer.email`, which becomes `customer.email_address`.

**Tasks.**

1. Add two endpoints and keep them in two versions of the API, in separate modules that run as separate processes: version 1 on port 8001 uses `email`, version 2 on port 8002 uses `email_address`.
   - `GET /customers/{customer_id}` returns the customer with its email.
   - `PUT /customers/{customer_id}/email` with body `{"email": string}` changes it.
2. Migration `expand`: add `email_address`, backfill it from `email`, and create a trigger that copies a change made to either column into the other.
3. With both versions running, change an email through version 1 and read it through version 2, then the other way round.
4. Migration `contract`: after stopping version 1, drop the trigger and the column `email`. Show that version 2 still works.
5. Show that `downgrade` of each migration works.

**Deliverables.**

- The two migrations, both API versions, and `check_versions.sh` (or `.py`) that runs the requests of task 3.
- `README.md` with the order of deployment steps and the output of `check_versions` after the expand migration and of version 2 after the contract migration.

**Done when.** After the expand migration a change made through either version is visible in the other, and after the contract migration version 2 works and `email` no longer exists.

## Resolução

Ficheiros entregues:

- [migrations/versions/0004_expand_email_address.py](migrations/versions/0004_expand_email_address.py): a migration `expand`. Acrescenta `email_address`, cria a função e o trigger `customer_sync_email` e faz o backfill a partir de `email`.
- [migrations/versions/0005_contract_email.py](migrations/versions/0005_contract_email.py): a migration `contract`. Apaga o trigger, a função e a coluna `email`. O `downgrade` volta ao estado depois da 0004.
- [app/v1.py](app/v1.py): a versão 1 da API (porta 8001). É o código de antes da mudança de nome e usa os modelos dessa versão, [app/models_v1.py](app/models_v1.py), com `customer.email`. Esse ficheiro é o `models.py` do exercício, sem o engine.
- [app/v2.py](app/v2.py): a versão 2 da API (porta 8002). Usa os modelos de [models.py](models.py), com `customer.email_address`.
- [app/rentals.py](app/rentals.py): os 3 endpoints de rentals do exercício (`POST /rentals`, `POST /rentals/{rental_id}/return` e `GET /rentals/overdue`), com o mesmo código. `rentals_router(models)` monta-os com os modelos de cada versão: a v1 passa `app.models_v1` e a v2 passa `models`. Cada versão tem assim a API completa do exercício e os dois endpoints novos de customers.
- [app/schemas.py](app/schemas.py): o contrato HTTP, igual nas duas versões. O body do `PUT` e a resposta continuam a usar `"email"`. A coluna muda de nome, a API não.
- [app/db.py](app/db.py): o engine e a dependência `get_session`, uma sessão por pedido.
- [check_versions.py](check_versions.py): os pedidos da tarefa 3 (`expand`) e da tarefa 4 (`contract`). Os dois modos também chamam os endpoints de rentals e devolvem no fim os alugueres que abrem, por isso o script pode correr várias vezes sobre a mesma base de dados.
- [models.py](models.py), [migrations/env.py](migrations/env.py) e as migrations 0001–0003: copiados do [exercício](../exercise/). Em `models.py`, `Customer` tem `email_address` em vez de `email`, porque os modelos descrevem o esquema em `head`. A base de dados é `ch12` (`CH12_DATABASE_URL`).
- [pyproject.toml](pyproject.toml), `uv.lock` e [alembic.ini](alembic.ini).

### Ordem dos passos de deployment

| Passo | Comando | Versões a correr | Esquema |
|---|---|---|---|
| 0. Ponto de partida | `alembic upgrade 0003_one_open_rental_per_copy` | v1 | `email` |
| 1. Expand | `alembic upgrade 0004_expand_email_address` | v1 | `email` + `email_address` + trigger |
| 2. Deploy da v2 | `uvicorn app.v2:app --port 8002` | v1 e v2 | idem |
| 3. Passar o tráfego todo para a v2 e parar a v1 | `kill` do processo da v1 | v2 | idem |
| 4. Contract | `alembic upgrade 0005_contract_email` | v2 | `email_address` |

A ordem é o que evita downtime. Em cada passo, o esquema serve todas as versões que estão a correr:

- **O expand vem antes da v2.** A v2 lê `email_address`, que só existe depois da 0004. A v1 continua a funcionar durante e depois da 0004, porque a migration só acrescenta (uma coluna nullable e um trigger).
- **O contract vem depois de parar a v1.** A v1 é o último código que usa `email`. Se ainda estivesse a correr, cada pedido falhava. Arranquei a v1 depois da 0005 para confirmar:

  ```
  $ curl http://127.0.0.1:8001/customers/1
  Internal Server Error -> 500
  $ curl 'http://127.0.0.1:8001/rentals/overdue?as_of=2026-07-31'
  Internal Server Error -> 500
  # no log da v1:
  sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedColumn) column customer.email does not exist
  ```

  Os endpoints de rentals também falham, apesar de não usarem o email: `session.get(Customer)` e o join com `customer` em `/rentals/overdue` carregam todas as colunas mapeadas, e `email` é uma delas. Uma mudança de nome não afeta só o código que usa a coluna, afeta todo o código que mapeia a tabela.

- **Entre os passos 1 e 3**, a v1 e a v2 escrevem cada uma na sua coluna, e o trigger mantém as duas iguais. Sem o trigger, uma alteração feita na v1 não aparecia na v2, e o contrário também.

### Como correr

```bash
# a partir da raiz do repositório
./scripts/create-db.sh ch12 --pagila --reset
cd exercises/12-api/challenge
uv sync
uv run alembic stamp 0001_baseline
uv run alembic upgrade 0003_one_open_rental_per_copy

uv run uvicorn app.v1:app --port 8001 &                    # passo 0
uv run alembic upgrade 0004_expand_email_address           # passo 1
uv run uvicorn app.v2:app --port 8002 &                    # passo 2
uv run python check_versions.py expand                     # tarefa 3
kill %1                                                    # passo 3: parar a v1
uv run alembic upgrade 0005_contract_email                 # passo 4
uv run python check_versions.py contract                   # tarefa 4
```

O URL por omissão é `postgresql+psycopg:///ch12`: o host, o utilizador e a password vêm de `PGHOST`, `PGUSER` e `PGPASSWORD`. Para outro destino, usar `CH12_DATABASE_URL`. Os URLs das duas versões mudam-se com `CH12_V1_URL` e `CH12_V2_URL`.

### Migration `expand` (0004)

1. `add_column customer.email_address text` nullable e sem default: só altera o catálogo, não reescreve a tabela.
2. `CREATE FUNCTION customer_sync_email()` e `CREATE TRIGGER customer_sync_email BEFORE INSERT OR UPDATE OF email, email_address ON customer FOR EACH ROW`:
   - num `UPDATE` que muda só `email` (a v1), copia para `email_address`;
   - num `UPDATE` que muda só `email_address` (a v2), copia para `email`;
   - num `INSERT`, preenche a coluna que vier a `NULL` com a outra;
   - num `UPDATE` que muda as duas, não faz nada: quem escreveu já as definiu.
3. `UPDATE customer SET email_address = email`, o backfill.

O trigger é `BEFORE` e altera `NEW`, a linha que vai ser escrita, em vez de correr outro `UPDATE`. Por isso não se dispara a si próprio. O `OF email, email_address` evita que corra em `UPDATE`s que não tocam no email.

O trigger é criado antes do backfill. Pela ordem contrária, uma linha alterada pela v1 entre o backfill e a criação do trigger ficava com `email_address` desatualizado. Aqui as duas coisas correm na mesma transação, e o `ADD COLUMN` tem um lock `ACCESS EXCLUSIVE` sobre `customer` até ao commit, por isso ninguém consegue escrever no meio. Numa tabela grande, o backfill seria feito em lotes, fora da transação da migration, e aí a ordem passa a ser essencial.

Testei o ramo do `INSERT` numa transação que acabou em `ROLLBACK`:

```
 first_name |      email      |  email_address
------------+-----------------+-----------------
 V1         | v1@example.com  | v1@example.com     -- INSERT só com email
 V2         | v2@example.com  | v2@example.com     -- INSERT sem email, depois UPDATE de email_address
 V2b        | v2b@example.com | v2b@example.com    -- INSERT só com email_address
```

### Tarefa 3: `check_versions.py expand`, depois da 0004 com as duas versões a correr

```
--- both versions read the same email
GET http://127.0.0.1:8001/customers/1 -> 200 {'customer_id': 1, 'first_name': 'MARY', 'last_name': 'SMITH', 'email': 'MARY.SMITH@sakilacustomer.org'}
GET http://127.0.0.1:8002/customers/1 -> 200 {'customer_id': 1, 'first_name': 'MARY', 'last_name': 'SMITH', 'email': 'MARY.SMITH@sakilacustomer.org'}
  OK   version 1 and version 2 return the same customer

--- write through version 1 (email), read through version 2 (email_address)
PUT http://127.0.0.1:8001/customers/1/email {'email': 'mary.smith.v1@example.com'} -> 200 {'customer_id': 1, 'first_name': 'MARY', 'last_name': 'SMITH', 'email': 'mary.smith.v1@example.com'}
  database: email = 'mary.smith.v1@example.com', email_address = 'mary.smith.v1@example.com'
GET http://127.0.0.1:8002/customers/1 -> 200 {'customer_id': 1, 'first_name': 'MARY', 'last_name': 'SMITH', 'email': 'mary.smith.v1@example.com'}
  OK   version 2 sees the change

--- write through version 2 (email_address), read through version 1 (email)
PUT http://127.0.0.1:8002/customers/1/email {'email': 'mary.smith.v2@example.com'} -> 200 {'customer_id': 1, 'first_name': 'MARY', 'last_name': 'SMITH', 'email': 'mary.smith.v2@example.com'}
  database: email = 'mary.smith.v2@example.com', email_address = 'mary.smith.v2@example.com'
GET http://127.0.0.1:8001/customers/1 -> 200 {'customer_id': 1, 'first_name': 'MARY', 'last_name': 'SMITH', 'email': 'mary.smith.v2@example.com'}
  OK   version 1 sees the change

--- rentals: both versions work on the same rows
GET http://127.0.0.1:8001/rentals/overdue?as_of=2026-07-31 -> 200, 229 items
GET http://127.0.0.1:8002/rentals/overdue?as_of=2026-07-31 -> 200, 229 items
  OK   same overdue list, 229 items
POST http://127.0.0.1:8001/rentals {'customer_id': 2, 'film_id': 7, 'store_id': 1, 'staff_id': 6} -> 201 {'rental_id': 87560, 'inventory_id': 32}
POST http://127.0.0.1:8002/rentals {'customer_id': 3, 'film_id': 7, 'store_id': 1, 'staff_id': 6} -> 201 {'rental_id': 87561, 'inventory_id': 33}
  OK   one copy rented through each version
POST http://127.0.0.1:8001/rentals {'customer_id': 4, 'film_id': 7, 'store_id': 1, 'staff_id': 6} -> 409 {'detail': 'no copy of this film is available in this store'}
  OK   no copy left for version 1
POST http://127.0.0.1:8002/rentals/87560/return -> 200 {'rental_id': 87560, 'return_date': '2026-10-30T21:55:35.931049Z'}
  OK   version 2 returns the rental opened by version 1
POST http://127.0.0.1:8001/rentals/87560/return -> 409 {'detail': 'rental already returned'}
  OK   version 1 sees it returned
POST http://127.0.0.1:8001/rentals/87561/return -> 200 {'rental_id': 87561, 'return_date': '2026-10-30T21:55:35.955055Z'}
  OK   version 1 returns the rental opened by version 2

OK
```

### Tarefa 4: depois de parar a v1 e da 0005

```
$ uv run python check_versions.py contract
--- version 1 is stopped
GET http://127.0.0.1:8001/customers/1 -> [Errno 111] Connection refused
  OK   version 1 does not answer

--- customer.email no longer exists
  email columns of customer: ['email_address']
  OK   only email_address is left

--- version 2 still works
PUT http://127.0.0.1:8002/customers/1/email {'email': 'mary.smith.contract@example.com'} -> 200 {'customer_id': 1, 'first_name': 'MARY', 'last_name': 'SMITH', 'email': 'mary.smith.contract@example.com'}
  database: email_address = 'mary.smith.contract@example.com'
GET http://127.0.0.1:8002/customers/1 -> 200 {'customer_id': 1, 'first_name': 'MARY', 'last_name': 'SMITH', 'email': 'mary.smith.contract@example.com'}
  OK   version 2 reads its own change

--- rentals through version 2
GET http://127.0.0.1:8002/rentals/overdue?as_of=2026-07-31 -> 200, 229 items
  OK   overdue list has 229 items
POST http://127.0.0.1:8002/rentals {'customer_id': 2, 'film_id': 7, 'store_id': 1, 'staff_id': 6} -> 201 {'rental_id': 87564, 'inventory_id': 32}
  OK   rent a copy
POST http://127.0.0.1:8002/rentals/87564/return -> 200 {'rental_id': 87564, 'return_date': '2026-10-30T21:55:37.570359Z'}
  OK   return it

OK
```

`\d customer` depois da 0005 (sem a secção `Referenced by`): `email` desapareceu, `email_address` ficou como última coluna, e o trigger `customer_sync_email` também já não existe.

```
                                             Table "public.customer"
     Column     |           Type           | Collation | Nullable |                    Default
----------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id    | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id       | integer                  |           | not null |
 first_name     | text                     |           | not null |
 last_name      | text                     |           | not null |
 address_id     | integer                  |           | not null |
 activebool     | boolean                  |           | not null | true
 create_date    | date                     |           | not null | CURRENT_DATE
 last_update    | timestamp with time zone |           |          | now()
 active         | integer                  |           |          |
 uuid           | uuid                     |           | not null | uuidv7()
 loyalty_points | integer                  |           | not null | 0
 email_address  | text                     |           |          |
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)
Foreign-key constraints:
    "customer_address_id_fkey" FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "customer_store_id_fkey" FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE ON DELETE RESTRICT
Triggers:
    last_updated BEFORE UPDATE ON customer FOR EACH ROW EXECUTE FUNCTION last_updated()

```

Em `head`, `alembic check` não encontra diferenças entre `models.py` e a base de dados (`No new upgrade operations detected.`).

### Tarefa 5: `downgrade` de cada migration

**`downgrade` da 0005 (contract).** Volta ao estado depois da 0004: recria `email`, preenche-a a partir de `email_address` e recria o trigger. O último email escrito pela v2 depois do contract aparece nas duas colunas:

```
$ uv run alembic downgrade 0004_expand_email_address
INFO  [alembic.runtime.migration] Running downgrade 0005_contract_email -> 0004_expand_email_address, contract: drop customer.email and the sync trigger
$ psql -d ch12 -c "SELECT email, email_address FROM customer WHERE customer_id = 1" -c "SELECT tgname FROM pg_trigger WHERE tgrelid = 'customer'::regclass AND NOT tgisinternal"
              email              |          email_address
---------------------------------+---------------------------------
 mary.smith.contract@example.com | mary.smith.contract@example.com
(1 row)

       tgname
---------------------
 last_updated
 customer_sync_email
(2 rows)

```

Com a v1 arrancada outra vez, `check_versions.py expand` volta a passar (o output é igual ao da tarefa 3, incluindo os rentals, e termina em `OK`).

**`downgrade` da 0004 (expand).** Apaga o trigger, a função e `email_address`. Não se perde nada: o trigger copiou para `email` tudo o que a v2 escreveu. A v1 lê o último email escrito pela v2, e a v2 deixa de funcionar porque `email_address` já não existe. O mesmo acontece com os rentals: `GET /rentals/overdue` dá `200` na v1 e `500` na v2. No fim, `upgrade head` volta a correr as duas migrations sem erros:

```
$ uv run alembic downgrade 0003_one_open_rental_per_copy
INFO  [alembic.runtime.migration] Running downgrade 0004_expand_email_address -> 0003_one_open_rental_per_copy, expand: customer.email_address next to customer.email, kept in sync by a trigger
$ psql -d ch12 -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'customer' AND column_name LIKE 'email%'" -c "SELECT tgname FROM pg_trigger WHERE tgrelid = 'customer'::regclass AND NOT tgisinternal"
 column_name
-------------
 email
(1 row)

    tgname
--------------
 last_updated
(1 row)

$ curl http://127.0.0.1:8002/customers/1   # versão 2
Internal Server Error -> 500
$ curl http://127.0.0.1:8001/customers/1   # versão 1
{"customer_id":1,"first_name":"MARY","last_name":"SMITH","email":"mary.smith.v2@example.com"} -> 200
$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade 0003_one_open_rental_per_copy -> 0004_expand_email_address, expand: customer.email_address next to customer.email, kept in sync by a trigger
INFO  [alembic.runtime.migration] Running upgrade 0004_expand_email_address -> 0005_contract_email, contract: drop customer.email and the sync trigger
```

Depois do segundo `upgrade head`, `check_versions.py contract` passou outra vez.

O `downgrade` da 0005 é o caminho para desfazer o passo 4 sem downtime. A v2 pode continuar a correr durante o downgrade, porque `email_address` não muda. Depois dele, `email` tem os valores atuais e o trigger volta a manter as duas colunas iguais, por isso a v1 pode voltar a arrancar ao lado da v2.
