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

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [ ] `roles.sql` with `ex09_migrations`, `ex09_app`, `ex09_readonly` and default privileges
- [ ] `proofs.sql` with the 4 proofs and expected outcome in comments
- [ ] API with `POST /actors`, `POST /notes`, `POST /counters/{name}` and `.env.example`
- [ ] Injection proofs: SQL payload stored as text, `$ne` -> `422`, invalid counter names -> `422`
