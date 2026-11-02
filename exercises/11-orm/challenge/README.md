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

## Resolução

Ficheiros entregues:

- [models.py](models.py): uma cópia dos modelos do [exercício](../exercise/models.py) (só muda a base, `ch11`, e a variável `CH11_DATABASE_URL`), para o desafio correr sozinho. Os 6 modelos (`Film`, `Language`, `Actor`, `Category`, `FilmActor` e `FilmCategory`) com `Mapped` e `mapped_column`. `Film` tem `language`, `actors` e `categories`, e `Actor` e `Category` têm `films`.
- [queries.py](queries.py): `films_with_actors_and_categories()`, a query testada. Carrega os primeiros 100 filmes por `film_id` com `selectinload(Film.actors)` e `selectinload(Film.categories)`.
- [tests/conftest.py](tests/conftest.py): as fixtures `engine`, `session`, `statements` e `assert_max_queries`.
- [tests/test_queries.py](tests/test_queries.py): o teste.
- [pyproject.toml](pyproject.toml) e `uv.lock`.

### Como funciona

- A fixture `statements` regista um listener de `before_cursor_execute` no engine. O listener junta cada statement SQL a uma lista, e a fixture remove-o no fim do teste.
- `assert_max_queries(n)` é um context manager. Guarda o tamanho da lista à entrada do `with` e, à saída, conta só os statements que correram dentro do bloco. Se forem mais de `n`, chama `pytest.fail` com o número de statements e as primeiras 5 linhas de SQL.
- O teste corre a query dentro de `assert_max_queries(3)`. Fora do bloco, compara o número total de pares filme–ator e filme–categoria com SQL escrito à mão. Esta query de verificação não entra na contagem.
- Com `selectinload`, são 3 statements: um para os filmes, um para os atores dos 100 filmes (`WHERE film.film_id IN (...)`) e um para as categorias.

Nota: nesta cópia do Pagila, um filme pode ter mais do que uma categoria (`ACADEMY DINOSAUR` tem `Games`, `New` e `Travel`), por isso o teste não fixa as categorias de um filme. Compara os totais com a base de dados.

### Como correr

```bash
# a partir da raiz do repositório
psql -d postgres -c 'CREATE DATABASE ch11 TEMPLATE pagila;'   # ou ./scripts/create-db.sh ch11 --pagila --reset
cd exercises/11-orm/challenge
uv sync
uv run pytest -v
```

O URL por omissão é `postgresql+psycopg:///ch11`: o host, o utilizador e a password vêm de `PGHOST`, `PGUSER` e `PGPASSWORD`. Para outro destino, usar `CH11_DATABASE_URL`.

### Com eager loading: passa

```
$ uv run pytest -v
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.2.0, pluggy-1.7.0 -- /workspaces/databases_module/exercises/11-orm/challenge/.venv/bin/python
cachedir: .pytest_cache
rootdir: /workspaces/databases_module/exercises/11-orm/challenge
configfile: pyproject.toml
testpaths: tests
collecting ... collected 1 item

tests/test_queries.py::test_first_100_films_with_actors_and_categories PASSED [100%]

============================== 1 passed in 0.08s ===============================
```

### Sem eager loading: falha

Tirei a linha `.options(selectinload(Film.actors), selectinload(Film.categories))` de [queries.py](queries.py):

```
$ uv run pytest -v
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.2.0, pluggy-1.7.0 -- /workspaces/databases_module/exercises/11-orm/challenge/.venv/bin/python
cachedir: .pytest_cache
rootdir: /workspaces/databases_module/exercises/11-orm/challenge
configfile: pyproject.toml
testpaths: tests
collecting ... collected 1 item

tests/test_queries.py::test_first_100_films_with_actors_and_categories FAILED [100%]

=================================== FAILURES ===================================
_______________ test_first_100_films_with_actors_and_categories ________________
expected at most 3 statements, 201 ran. First ones:
  1. SELECT film.film_id, film.title, film.description, film.language_id, film.length, film.last_update  ...
  2. SELECT actor.actor_id, actor.first_name, actor.last_name, actor.last_update  ...
  3. SELECT category.category_id, category.name, category.last_update  ...
  4. SELECT actor.actor_id, actor.first_name, actor.last_name, actor.last_update  ...
  5. SELECT category.category_id, category.name, category.last_update  ...
=========================== short test summary info ============================
FAILED tests/test_queries.py::test_first_100_films_with_actors_and_categories
============================== 1 failed in 0.14s ===============================
```

201 = 1 query para os filmes + 100 para `film.actors` + 100 para `film.categories`. É o N+1 a dobrar: cada acesso a uma relação lazy de cada filme é um `SELECT` novo. Os statements alternam entre `actor` e `category` porque o código lê os atores e as categorias de cada filme antes de passar ao seguinte.

Depois voltei a pôr o `selectinload` e o teste voltou a passar (3 statements).
