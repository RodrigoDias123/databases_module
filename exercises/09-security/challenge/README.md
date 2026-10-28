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
