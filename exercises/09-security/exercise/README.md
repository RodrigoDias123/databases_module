# Exercício 09: Security

## Enunciado

Folder: `exercises/09-security/exercise/`

**Goal.** Apply least privilege in the three engines and write to each of them from an API without injection.

**Starting point.** A fresh copy of Pagila (`./scripts/create-db.sh ex09 --pagila --reset`). Roles exist for the whole PostgreSQL server, not per database, so this exercise uses the prefix `ex09_` to avoid clashing with the roles of the tutorial. For the API, use the stack you chose; `sessions/09-security/` has example projects in FastAPI, Django and Next.js. Credentials come from environment variables, never from the code.

**Tasks.**

1. `roles.sql`, run as `postgres` on `ex09`: create the login roles `ex09_migrations`, `ex09_app` and `ex09_readonly`, make `ex09_migrations` the owner of the database, remove `CREATE` on schema `public` from `PUBLIC`, and grant:
   - `ex09_app`: `SELECT`, `INSERT`, `UPDATE`, `DELETE` on every table and `USAGE` on every sequence;
   - `ex09_readonly`: `SELECT` on every table;
   - default privileges so that tables created later by `ex09_migrations` get the same grants.

2. `proofs.sql`, run as `postgres`, using `SET ROLE` and `RESET ROLE`, with the expected outcome in a comment above each statement:
   - as `ex09_app`, `DROP TABLE film` fails;
   - as `ex09_app`, `INSERT INTO actor (first_name, last_name) VALUES ('X', 'Y')` works;
   - as `ex09_readonly`, `SELECT count(*) FROM film` works;
   - as `ex09_readonly`, the same `INSERT` fails.

3. An API with 3 endpoints, each writing to one engine with the users of tasks 1 and 3:
   - `POST /actors` with body `{"first_name": string, "last_name": string}` inserts a row into `actor` with a parameterised query and returns `201` with the new `actor_id`.
   - `POST /notes` with body `{"customer_id": integer, "text": string}` inserts a document into the collection `notes` of the database `ex09`. Any other type in the body returns `422`.
   - `POST /counters/{name}` runs `INCR counter:{name}` and returns `200` with the new value. A `name` that does not match `^[a-z0-9_-]{1,32}$` returns `422`.
4. Prove that the API is safe by sending these requests and showing the response and what was stored:
   - `POST /actors` with `{"first_name": "x'); DROP TABLE actor; --", "last_name": "y"}`: the text is stored as it is and `actor` still exists;
   - `POST /notes` with `{"customer_id": 1, "text": {"$ne": null}}`: `422`;
   - `POST /counters/a*` and `POST /counters/x:y`: `422`.

**Deliverables.**

- `roles.sql`, `proofs.sql`
- The API project, with a `.env.example` listing the variables it needs.
- `README.md` with the commands to run everything, the output of `proofs.sql`, the requests and responses of task 5 (for example as `curl` commands and their output) and the output of task 6. Note that `ACL SETUSER` is lost when Redis restarts unless it is saved to an ACL file, and say how you would keep it.

**Done when.** Every proof in tasks 2 shows the expected outcome, and no query in the API is built by concatenating user input.

## Challenge (opcional, em `challenge/`)

Enunciado completo em [challenge/README.md](../challenge/README.md).

## Checklist

- [x] `roles.sql` with `ex09_migrations`, `ex09_app`, `ex09_readonly` and default privileges
- [x] `proofs.sql` with the 4 proofs and expected outcome in comments
- [x] API with `POST /actors`, `POST /notes`, `POST /counters/{name}` and `.env.example`
- [x] Injection proofs: SQL payload stored as text, `$ne` -> `422`, invalid counter names -> `422`

## Resolução

Ficheiros entregues:

- [roles.sql](roles.sql): os 3 roles, o `REVOKE` em `public` e os `GRANT` e default privileges. Lê as passwords de variáveis de ambiente com `\getenv` e pode correr outra vez.
- [proofs.sql](proofs.sql): as 4 provas, cada uma numa transação com `ROLLBACK`.
- [api/](api/): a API em FastAPI ([app/main.py](api/app/main.py), [app/clients.py](api/app/clients.py)), os scripts que criam os utilizadores de MongoDB e Redis ([scripts/setup_mongo.py](api/scripts/setup_mongo.py), [scripts/setup_redis.py](api/scripts/setup_redis.py)) e o [.env.example](api/.env.example).

O enunciado fala em "tasks 1 and 3" para os utilizadores e em "task 5" e "task 6" para os pedidos, mas só tem 4 tarefas. Os utilizadores de MongoDB e Redis não aparecem em nenhuma tarefa, por isso criei-os em `setup_mongo.py` e `setup_redis.py`. Os pedidos e respostas correspondem à tarefa 4.

### Utilizadores

| Motor | Utilizador | Privilégios |
|-------|------------|-------------|
| PostgreSQL | `ex09_migrations` | dono da base `ex09`, `CREATE` no schema `public` |
| PostgreSQL | `ex09_app` | `SELECT, INSERT, UPDATE, DELETE` em todas as tabelas, `USAGE` nas sequências |
| PostgreSQL | `ex09_readonly` | `SELECT` em todas as tabelas |
| MongoDB | `ex09_app` (criado na base `ex09`) | `readWrite` só na base `ex09` |
| Redis | `ex09_app` | `~counter:* -@all +incr +select`: só `INCR`, só em chaves `counter:*` |

O schema `public` da Pagila pertence ao `postgres`, por isso ser dono da base não chega: o `ex09_migrations` também precisa de `CREATE` no schema. Sem esse `GRANT` não podia criar tabelas, e as default privileges nunca seriam usadas.

No Redis o utilizador só pode correr o comando de que a API precisa. O `+select` é preciso porque o URL escolhe a base 9 e o cliente envia `SELECT 9` ao ligar.

### Como correr

A partir da root do repositório. As passwords vêm do ambiente, nunca do código:

```bash
docker compose up -d
./scripts/create-db.sh ex09 --pagila --reset

cp exercises/09-security/exercise/api/.env.example exercises/09-security/exercise/api/.env   # mudar as passwords
set -a; source exercises/09-security/exercise/api/.env; set +a

psql -d ex09 -v ON_ERROR_STOP=1 -f exercises/09-security/exercise/roles.sql
psql -d ex09 -e -f exercises/09-security/exercise/proofs.sql
```

O `proofs.sql` corre sem `ON_ERROR_STOP`, porque duas das provas têm de falhar.

A API:

```bash
cd exercises/09-security/exercise/api
uv sync
uv run python -m scripts.setup_mongo
uv run python -m scripts.setup_redis
uv run uvicorn app.main:app --port 8000
```

### Output de `proofs.sql`

```
BEGIN;
SET ROLE ex09_app;
SELECT current_user;
 current_user
--------------
 ex09_app
(1 row)

DROP TABLE film;
psql:exercises/09-security/exercise/proofs.sql:14: ERROR:  must be owner of table film
ROLLBACK;
RESET ROLE;

BEGIN;
SET ROLE ex09_app;
SELECT current_user;
 current_user
--------------
 ex09_app
(1 row)

INSERT INTO actor (first_name, last_name) VALUES ('X', 'Y') RETURNING actor_id, first_name, last_name;
 actor_id | first_name | last_name
----------+------------+-----------
      201 | X          | Y
(1 row)

INSERT 0 1
ROLLBACK;
RESET ROLE;

BEGIN;
SET ROLE ex09_readonly;
SELECT current_user;
 current_user
---------------
 ex09_readonly
(1 row)

SELECT count(*) FROM film;
 count
-------
  1000
(1 row)

ROLLBACK;
RESET ROLE;

BEGIN;
SET ROLE ex09_readonly;
SELECT current_user;
 current_user
---------------
 ex09_readonly
(1 row)

INSERT INTO actor (first_name, last_name) VALUES ('X', 'Y');
psql:exercises/09-security/exercise/proofs.sql:41: ERROR:  permission denied for table actor
ROLLBACK;
RESET ROLE;

SELECT current_user;
 current_user
--------------
 postgres
(1 row)
```

| # | Role | Instrução | Esperado | Resultado |
|---|------|-----------|----------|-----------|
| 1 | `ex09_app` | `DROP TABLE film` | falha | `must be owner of table film` |
| 2 | `ex09_app` | `INSERT INTO actor ...` | funciona | `actor_id` 201 |
| 3 | `ex09_readonly` | `SELECT count(*) FROM film` | funciona | 1000 |
| 4 | `ex09_readonly` | `INSERT INTO actor ...` | falha | `permission denied for table actor` |

O `DROP` falha por falta de dono, não por falta de um `GRANT`: em PostgreSQL só o dono de uma tabela (ou um superuser) a pode apagar, e nenhum `GRANT` dá esse direito. O `ROLLBACK` desfaz o `INSERT`, mas não a sequência, por isso o próximo actor recebe o 202.

**Default privileges.** O `\ddp` mostra as regras para as tabelas que o `ex09_migrations` criar:

```
      Owner      | Schema |   Type   |        Access privileges
-----------------+--------+----------+---------------------------------
 ex09_migrations | public | sequence | ex09_app=U/ex09_migrations
 ex09_migrations | public | table    | ex09_readonly=r/ex09_migrations+
                 |        |          | ex09_app=arwd/ex09_migrations
```

E funcionam numa tabela nova, sem nenhum `GRANT` novo:

```
SET ROLE ex09_migrations;  CREATE TABLE ex09_probe (id serial PRIMARY KEY, x int);   -- CREATE TABLE
SET ROLE ex09_app;         INSERT INTO ex09_probe (x) VALUES (1) RETURNING id;       -- id = 1
SET ROLE ex09_readonly;    SELECT count(*) FROM ex09_probe;                          -- 1
SET ROLE ex09_readonly;    INSERT INTO ex09_probe (x) VALUES (2);                    -- ERROR: permission denied for table ex09_probe
SET ROLE ex09_migrations;  DROP TABLE ex09_probe;                                    -- DROP TABLE
```

### A API

| Endpoint | Motor | Defesa |
|----------|-------|--------|
| `POST /actors` | PostgreSQL, como `ex09_app` | Query parametrizada: `VALUES (%s, %s)`. O texto SQL e os valores vão em separado, e o servidor nunca lê os valores como SQL. |
| `POST /notes` | MongoDB, como `ex09_app` | Modelo Pydantic com `StrictInt`, `StrictStr` e `extra="forbid"`. Um objeto como `{"$ne": null}` não é uma string, por isso é `422` antes de chegar ao MongoDB. O documento é construído campo a campo, nunca a partir do JSON em bruto. |
| `POST /counters/{name}` | Redis, como `ex09_app` | O `name` tem de corresponder a `^[a-z0-9_-]{1,32}$`. Sem `*`, `?` ou `[` não há padrões glob, e sem `:` não se sai do prefixo `counter:`. |

Nenhuma query junta texto do utilizador ao código. A única string montada é a chave do Redis, `f"counter:{name}"`, que é um valor (o Redis não a interpreta como comando) e só é montada depois de o `name` passar a regex. Mesmo que a validação falhasse, o ACL só deixa correr `INCR` em `counter:*`.

`StrictInt` também recusa `"customer_id": "1"`. Sem ele o Pydantic convertia a string para 1, o que aqui não seria perigoso, mas o enunciado pede `422` para qualquer outro tipo.

### Pedidos e respostas

**SQL injection em `POST /actors`:**

```
$ curl -s -i -X POST localhost:8000/actors -H 'content-type: application/json' \
    -d '{"first_name": "x'"'"'); DROP TABLE actor; --", "last_name": "y"}'
HTTP/1.1 201 Created
content-type: application/json

{"actor_id":202}
```

O que ficou guardado:

```
$ psql -d ex09 -c "SELECT actor_id, first_name, last_name FROM actor ORDER BY actor_id DESC LIMIT 1"
 actor_id |        first_name         | last_name
----------+---------------------------+-----------
      202 | x'); DROP TABLE actor; -- | y

$ psql -d ex09 -c "SELECT to_regclass('actor') AS still_exists, count(*) FROM actor"
 still_exists | count
--------------+-------
 actor        |   201
```

O payload ficou guardado como texto, e a `actor` continua a existir (200 linhas da Pagila mais esta). Com concatenação, `'x'); DROP TABLE actor; --'` fecharia o `VALUES` e acrescentaria um `DROP`. Mesmo nesse caso o `ex09_app` não o podia correr, como mostra a prova 1.

**NoSQL injection em `POST /notes`:**

```
$ curl -s -i -X POST localhost:8000/notes -H 'content-type: application/json' \
    -d '{"customer_id": 1, "text": {"$ne": null}}'
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{"detail":[{"type":"string_type","loc":["body","text"],"msg":"Input should be a valid string","input":{"$ne":null}}]}

$ curl -s -i -X POST localhost:8000/notes -H 'content-type: application/json' \
    -d '{"customer_id": "1", "text": "hello"}'
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{"detail":[{"type":"int_type","loc":["body","customer_id"],"msg":"Input should be a valid integer","input":"1"}]}
```

**Nomes de contadores inválidos em `POST /counters/{name}`:**

```
$ curl -s -i -X POST 'localhost:8000/counters/a*'
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{"detail":[{"type":"string_pattern_mismatch","loc":["path","name"],"msg":"String should match pattern '^[a-z0-9_-]{1,32}$'","input":"a*","ctx":{"pattern":"^[a-z0-9_-]{1,32}$"}}]}

$ curl -s -i -X POST 'localhost:8000/counters/x:y'
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{"detail":[{"type":"string_pattern_mismatch","loc":["path","name"],"msg":"String should match pattern '^[a-z0-9_-]{1,32}$'","input":"x:y","ctx":{"pattern":"^[a-z0-9_-]{1,32}$"}}]}
```

Os quatro `422` vêm do FastAPI, antes de qualquer ligação ao MongoDB ou ao Redis.

**Contador válido em `POST /counters/{name}`:**

```
$ curl -s -i -X POST localhost:8000/counters/visits
HTTP/1.1 200 OK
content-type: application/json

{"name":"visits","value":1}

$ curl -s -X POST localhost:8000/counters/visits
{"name":"visits","value":2}

$ redis-cli -n 9 GET counter:visits
"2"
```

### O utilizador do Redis

Output de `uv run python -m scripts.setup_redis`:

```
ACL SETUSER ex09_app reset on >*** ~counter:* -@all +incr +select
INCR counter:probe   -> 1
INCR other:probe     -> No permissions to access a key
GET counter:probe    -> User ex09_app has no permissions to run the 'get' command
KEYS *               -> User ex09_app has no permissions to run the 'keys' command
FLUSHALL             -> User ex09_app has no permissions to run the 'flushall' command
```

O `r.incr()` do redis-py não envia `INCR`, envia `INCRBY name 1`, e o ACL recusou-o. A API envia exatamente `INCR` com `r.execute_command("INCR", ...)`. Assim o ACL continua com um único comando de escrita.

### Variáveis de ambiente e `override=True`

O dev container já define `REDIS_URL` e `MONGO_URL` no ambiente, com os utilizadores `default` e `root`. O `load_dotenv()` não substitui variáveis que já existem, por isso na primeira versão a API ligava-se ao Redis como `default`, sem ACL e na base 0, mesmo com o `.env` correto. O código não mostrava o erro: o `INCR` funcionava na mesma. Por isso todos os ficheiros usam `load_dotenv(override=True)`, e o `.env` do projeto ganha sempre. O `DATABASE_URL` não está no ambiente do dev container, por isso o PostgreSQL usou sempre o `ex09_app`.

### O utilizador do MongoDB

Output de `uv run python -m scripts.setup_mongo`:

```
created user ex09_app on ex09 with readWrite on ex09 only
connected as [{'user': 'ex09_app', 'db': 'ex09'}]
insert into ex09_other: refused (Unauthorized)
```

**Nota válida em `POST /notes`:**

```
$ curl -s -i -X POST localhost:8000/notes -H 'content-type: application/json' \
    -d '{"customer_id": 1, "text": "hello"}'
HTTP/1.1 201 Created
content-type: application/json

{"id":"6ae50031d91c7100a5450472"}
```

O que ficou guardado em `ex09.notes` (o pedido com `{"$ne": null}` deu `422` e não guardou nada):

```
[
  { _id: ObjectId('6ae50031d91c7100a5450472'), customer_id: 1, text: 'hello' }
]
```

### O ACL do Redis não sobrevive a um restart

`ACL SETUSER` só altera a memória do servidor. No `docker-compose.yml` o Redis arranca só com `--requirepass` e sem ficheiro de ACL, por isso depois de um restart o `ex09_app` deixa de existir e a API falha a autenticação até se correr outra vez `setup_redis.py`.

Para o manter, configurava um ficheiro de ACL no arranque e guardava os utilizadores nele:

```yaml
redis:
  command: ["redis-server", "--aclfile", "/data/users.acl"]
```

Depois de cada `ACL SETUSER` corria `ACL SAVE`, que escreve os utilizadores em `/data/users.acl` (no volume `redis_data`, por isso sobrevive também a recriar o container). No arranque o Redis carrega o ficheiro sozinho, e `ACL LOAD` volta a lê-lo sem restart. A password do `default` também passa a ser uma linha do ficheiro (`user default on >... ~* &* +@all`), em vez do `--requirepass`. A alternativa é pôr as linhas `user ...` no `redis.conf`, mas assim `ACL SAVE` não funciona e cada alteração tem de ser feita à mão no ficheiro. Em ambos os casos o ficheiro tem as passwords (em SHA-256), por isso não vai para o Git.
