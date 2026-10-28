# Challenge 11: ORM I, SQLAlchemy

Opcional.

## Enunciado

Folder: `exercises/11-orm/challenge/`

**Goal.** Turn the absence of N+1 into an automated test.

**Starting point.** The models of the exercise above (or your own models of the same 6 tables) and `uv add pytest`.

**Tasks.**

1. In `tests/conftest.py`, write a pytest fixture that counts the SQL statements an engine runs, using SQLAlchemy's `before_cursor_execute` event.
2. Write a helper `assert_max_queries(n)`, used as a context manager, that fails the test if more than `n` statements ran inside the `with` block.
3. In `tests/test_queries.py`, write a test that lists the first 100 films with their actors and their categories inside `assert_max_queries(3)`.
4. Remove the eager loading from the query, run the test and show it failing with the number of statements. Put the eager loading back.

**Deliverables.**

- `tests/conftest.py`, `tests/test_queries.py` and the code they test.
- `README.md` with `uv run pytest -v` output for the passing test and for the failing one.

**Done when.** The test passes with eager loading and fails without it, and the failure message shows how many statements ran.
