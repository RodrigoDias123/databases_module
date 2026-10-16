# Exercício 03: SQL DDL, data types and constraints

## Enunciado

Folder: `exercises/03-ddl/`

1. `schema.sql`, runnable on an empty PostgreSQL database, implementing your library model from exercise 02. Include at least one `CHECK`, one composite `UNIQUE`, and one foreign key whose `ON DELETE` is justified in a comment.
2. `invalid.sql` with 5 `INSERT` statements that must fail, each with a comment naming the constraint that rejects it.

Marked 2 when the schema runs without errors and the 5 invalid inserts fail for the stated reason.

Group project: first version of the group's ER model (Mermaid in the README), reviewed by the trainer.

## Challenge (opcional, em `challenge/`)

Make the database reject invalid ISBNs. Create a `DOMAIN isbn13` over `text` whose `CHECK` validates both the format (13 digits, optional hyphens) and the check digit, using an `IMMUTABLE` SQL function. Use the domain in your `book` table. Prove that a valid ISBN is accepted, and that one with a wrong check digit is rejected. Explain why the function should be `IMMUTABLE`.
