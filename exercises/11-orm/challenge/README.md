# Challenge 11: ORM I, SQLAlchemy

Obrigatório.

## Enunciado

Write a pytest fixture that counts SQL statements using SQLAlchemy's `before_cursor_execute` event, and a test helper `assert_max_queries(n)` used as a context manager. Use it to write tests that fail if listing 100 films with actors and categories takes more than 3 queries. Introduce an N+1 and show the test catching it.
