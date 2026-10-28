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
