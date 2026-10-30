# Challenge 09: Security

Opcional.

## Enunciado

Folder: `exercises/09-security/challenge/`

**Goal.** Run the same API twice with users of different privileges and show that the database, not the code, stops the second one from writing.

**Starting point.** The API and users of the exercise above.

**Tasks.**

1. Add `GET /actors/{actor_id}`, `GET /notes?customer_id=` and `GET /counters/{name}` to the API.
2. Create read-only users: `ex09_readonly` already exists in PostgreSQL; add a MongoDB user `ex09_reader` with the role `read` on `ex09`, and a Redis ACL user `ex09_reader` that can only run `GET` on keys that start with `counter:`.
3. Run two instances of the same code: instance A on port 8001 with the users of the exercise, instance B on port 8002 with the read-only users. Only the environment variables differ.
4. Make every write endpoint return `403` when the engine refuses the write for lack of privilege: PostgreSQL SQLSTATE `42501`, a MongoDB `Unauthorized` error (code 13), or a Redis `NOPERM` error. Any other error stays a `500`.
5. Show that every `GET` works on both instances, and that every `POST` works on A and returns `403` on B.

**Deliverables.**

- The changed API project, with two example environment files (`.env.a.example` and `.env.b.example`).
- `README.md` with the commands to start both instances and the requests and responses of task 5.

**Done when.** The code has no check of which instance it is: the `403` responses come only from the privilege errors of the engines.

## Resolução

Ficheiros entregues, em [api/](api/), uma cópia da API do exercício com estas mudanças:

- [app/main.py](api/app/main.py): os 3 `GET` novos e os 3 exception handlers que transformam os erros de privilégio em `403`.
- [app/clients.py](api/app/clients.py): lê o ficheiro indicado em `ENV_FILE` (`.env.a` ou `.env.b`). É a única diferença entre as instâncias.
- [.env.a.example](api/.env.a.example) e [.env.b.example](api/.env.b.example): as mesmas 4 variáveis, com utilizadores diferentes.
- [.env.setup.example](api/.env.setup.example): as contas de admin e as passwords que os scripts de setup usam. Nenhuma instância lê este ficheiro, por isso nenhuma API tem credenciais de admin.
- [scripts/setup_mongo.py](api/scripts/setup_mongo.py) e [scripts/setup_redis.py](api/scripts/setup_redis.py): criam os utilizadores das duas instâncias.
- [.gitignore](api/.gitignore): o da raiz só ignora `.env` e `.env.local`. Sem este ficheiro, `.env.a`, `.env.b` e `.env.setup`, que têm passwords, iam para o Git.

### Utilizadores

| Motor | Instância A (8001) | Instância B (8002) |
|-------|--------------------|--------------------|
| PostgreSQL | `ex09_app`: `SELECT, INSERT, UPDATE, DELETE` | `ex09_readonly`: `SELECT` |
| MongoDB | `ex09_app`: `readWrite` em `ex09` | `ex09_reader`: `read` em `ex09` |
| Redis | `ex09_app`: `~counter:* -@all +incr +get +select` | `ex09_reader`: `~counter:* -@all +get +select` |

O `ex09_app` do Redis passou a ter também `+get`, porque a instância A precisa do `GET /counters/{name}`. O `+select` existe nos dois porque os URLs usam a base 9 e o cliente envia `SELECT 9` ao ligar. Não é um comando sobre chaves: o `ex09_reader` continua a só poder ler chaves `counter:*`.

Output do setup:

```
$ uv run python -m scripts.setup_mongo
updated user ex09_app on ex09: readWrite on ex09
created user ex09_reader on ex09: read on ex09

$ uv run python -m scripts.setup_redis
ACL SETUSER ex09_app reset on >*** ~counter:* -@all +incr +get +select
ACL SETUSER ex09_reader reset on >*** ~counter:* -@all +get +select
  ex09_app     GET counter:x      -> OK
  ex09_app     INCR counter:x     -> OK
  ex09_app     GET other:x        -> User ex09_app has no permissions to access the 'other:x' key
  ex09_app     SET counter:x 1    -> User ex09_app has no permissions to run the 'set' command
  ex09_reader  GET counter:x      -> OK
  ex09_reader  INCR counter:x     -> User ex09_reader has no permissions to run the 'incr' command
  ex09_reader  GET other:x        -> User ex09_reader has no permissions to access the 'other:x' key
  ex09_reader  SET counter:x 1    -> User ex09_reader has no permissions to run the 'set' command
```

### Como correr

Os roles de PostgreSQL e a base `ex09` vêm do exercício ([exercise/README.md](../exercise/README.md#como-correr)). A partir desta pasta:

```bash
cd exercises/09-security/challenge/api
cp .env.a.example .env.a
cp .env.b.example .env.b
cp .env.setup.example .env.setup        # mudar as passwords nos três
uv sync
uv run python -m scripts.setup_mongo
uv run python -m scripts.setup_redis

# dois terminais, o mesmo código
ENV_FILE=.env.a uv run uvicorn app.main:app --port 8001
ENV_FILE=.env.b uv run uvicorn app.main:app --port 8002
```

### Como o `403` aparece

O código não sabe em que instância está. Não há nenhuma variável `READ_ONLY` nem nenhum `if`: cada endpoint tenta escrever, e quem recusa é o motor. Três exception handlers olham só para o erro:

| Motor | Erro | Handler |
|-------|------|---------|
| PostgreSQL | `psycopg.Error` com `sqlstate == "42501"` (`insufficient_privilege`) | `403` |
| MongoDB | `OperationFailure` com `code == 13` (`Unauthorized`) | `403` |
| Redis | `redis.exceptions.NoPermissionError` (resposta `-NOPERM`) | `403` |

Para qualquer outro `psycopg.Error` ou `OperationFailure`, o handler volta a lançar a exceção e o FastAPI responde `500`. Erros de outras classes nem passam por estes handlers. A resposta do Mongo mostra só o `codeName`, porque a mensagem completa repete o comando interno inteiro (com o `lsid` da sessão).

### Pedidos e respostas

**`GET` nas duas instâncias:** os dois `200`, com os mesmos dados.

```
$ curl -s -i localhost:8001/actors/1
HTTP/1.1 200 OK
content-type: application/json

{"actor_id":1,"first_name":"PENELOPE","last_name":"GUINESS"}

$ curl -s -i localhost:8002/actors/1
HTTP/1.1 200 OK
content-type: application/json

{"actor_id":1,"first_name":"PENELOPE","last_name":"GUINESS"}

$ curl -s -i 'localhost:8001/notes?customer_id=7'
HTTP/1.1 200 OK
content-type: application/json

[{"id":"6ae500c45083fb3a2a1aae02","customer_id":7,"text":"from 8001"}]

$ curl -s -i 'localhost:8002/notes?customer_id=7'
HTTP/1.1 200 OK
content-type: application/json

[{"id":"6ae500c45083fb3a2a1aae02","customer_id":7,"text":"from 8001"}]

$ curl -s -i localhost:8001/counters/visits
HTTP/1.1 200 OK
content-type: application/json

{"name":"visits","value":3}

$ curl -s -i localhost:8002/counters/visits
HTTP/1.1 200 OK
content-type: application/json

{"name":"visits","value":3}
```

**`POST` na instância A:** todos funcionam.

```
$ curl -s -i -X POST localhost:8001/actors -H 'content-type: application/json' \
    -d '{"first_name": "Ana", "last_name": "Silva"}'
HTTP/1.1 201 Created
content-type: application/json

{"actor_id":204}

$ curl -s -i -X POST localhost:8001/notes -H 'content-type: application/json' \
    -d '{"customer_id": 7, "text": "from 8001"}'
HTTP/1.1 201 Created
content-type: application/json

{"id":"6ae500c45083fb3a2a1aae02"}

$ curl -s -i -X POST localhost:8001/counters/visits
HTTP/1.1 200 OK
content-type: application/json

{"name":"visits","value":3}
```

**`POST` na instância B:** os três dão `403`, cada um com o erro do seu motor.

```
$ curl -s -i -X POST localhost:8002/actors -H 'content-type: application/json' \
    -d '{"first_name": "Ana", "last_name": "Silva"}'
HTTP/1.1 403 Forbidden
content-type: application/json

{"detail":"postgres refused: permission denied for table actor"}

$ curl -s -i -X POST localhost:8002/notes -H 'content-type: application/json' \
    -d '{"customer_id": 7, "text": "from 8002"}'
HTTP/1.1 403 Forbidden
content-type: application/json

{"detail":"mongo refused: Unauthorized"}

$ curl -s -i -X POST localhost:8002/counters/visits
HTTP/1.1 403 Forbidden
content-type: application/json

{"detail":"redis refused: User ex09_reader has no permissions to run the 'incr' command"}
```

Depois disto não ficou nada da instância B: a `actor` só tem o 204 (`Ana Silva`, da A), a `notes` só tem a nota `from 8001`, e `counter:visits` continua a 3.

**Outro erro continua a ser `500`:** um `first_name` com um byte NUL dá `500` nas duas instâncias, porque o psycopg recusa-o antes de enviar a query (`psycopg.DataError: PostgreSQL text fields cannot contain NUL (0x00) bytes`, sem `sqlstate`). Não é um erro de privilégio, por isso não se transforma em `403`, nem na B:

```
$ curl -s -i -X POST localhost:8002/actors -H 'content-type: application/json' \
    -d '{"first_name": "A\u0000B", "last_name": "Silva"}'
HTTP/1.1 500 Internal Server Error
content-type: text/plain; charset=utf-8

Internal Server Error
```
