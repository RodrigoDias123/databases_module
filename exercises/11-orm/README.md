# Exercício 11: ORM I, SQLAlchemy

## Enunciado

Folder: `exercises/11-orm/`

1. Map 6 Pagila tables with their relationships.
2. Rewrite 3 queries from exercise 05 with the ORM and compare the generated SQL with your handwritten SQL.
3. Create an N+1 on purpose (list films and their actors), count the queries, fix it, and count again.

Marked 2 when all three points are done, with query counts before and after.

Group project: map your scenario's schema to SQLAlchemy models.

## Challenge (obrigatório, em `challenge/`)

Write a pytest fixture that counts SQL statements using SQLAlchemy's `before_cursor_execute` event, and a test helper `assert_max_queries(n)` used as a context manager. Use it to write tests that fail if listing 100 films with actors and categories takes more than 3 queries. Introduce an N+1 and show the test catching it.

## Checklist

- [ ] Map 6 Pagila tables with their relationships
- [ ] Rewrite 3 queries from exercise 05 with the ORM and compare the generated SQL
- [ ] Create an N+1 (films and actors), count queries, fix it, count again
