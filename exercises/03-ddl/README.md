# Exercício 03: SQL DDL, data types and constraints

## Enunciado

Folder: `exercises/03-ddl/exercise/`

**Goal.** Implement the municipal library in PostgreSQL with data types and constraints that enforce its rules.

**Starting point.** The library requirements in the exercise of session 02. You may implement your own model from that exercise or a corrected version of it. Create an empty database:

```bash
./scripts/create-db.sh ex03
```

**Tasks.**

1. Write `schema.sql`, which creates every table of the library. Use identity columns for surrogate keys, `numeric` for money and `timestamptz` or `date` for dates. Include at least:
   - one `CHECK` (for example the condition of a copy, or a due date after the loan date);
   - one composite `UNIQUE`;
   - one `ON DELETE RESTRICT` and one `ON DELETE CASCADE`, each justified in a comment.
2. Write `invalid.sql` with 5 `INSERT` or `DELETE` statements that must fail, each rejected by a different constraint. Above each statement, add a comment with the name of the constraint that rejects it.

Run the files in this order to check them:

```bash
docker compose exec -T postgres psql -U postgres -d ex03 -v ON_ERROR_STOP=1 < exercises/03-ddl/exercise/schema.sql
docker compose exec -T postgres psql -U postgres -d ex03 < exercises/03-ddl/exercise/invalid.sql
```

**Deliverables.**

- `schema.sql`, `invalid.sql`.
- `README.md` with the output of running `invalid.sql`.

**Done when.** `schema.sql` run on an empty database without errors, and each of the 5 statements in `invalid.sql` fails with the error of the constraint named in its comment.

## Challenge (obrigatório, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [ ] `schema.sql` creates every table of the library on an empty database (`ex03`)
- [ ] Identity columns for surrogate keys, `numeric` for money, `timestamptz` or `date` for dates
- [ ] At least one `CHECK`
- [ ] At least one composite `UNIQUE`
- [ ] One `ON DELETE RESTRICT` and one `ON DELETE CASCADE`, each justified in a comment
- [ ] `invalid.sql` with 5 statements, each rejected by a different constraint named in its comment
- [ ] `README.md` with the output of `invalid.sql`

## Resposta

Resposta em [exercise/README.md](exercise/README.md).
