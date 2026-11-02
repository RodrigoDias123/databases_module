# Exercício 11: ORM I, SQLAlchemy

## Enunciado

Folder: `exercises/11-orm/exercise/`

**Goal.** Map existing tables to ORM models, compare generated SQL with handwritten SQL, and find and fix an N+1.

**Starting point.** A fresh copy of Pagila and a uv project:

```bash
./scripts/create-db.sh ex11 --pagila --reset
uv init --bare
uv add "sqlalchemy>=2" "psycopg[binary]"
```

**Tasks.**

1. Map these 6 tables with SQLAlchemy 2.0 models (`Mapped`, `mapped_column`) and their relationships: `film`, `language`, `actor`, `film_actor`, `category`, `film_category`. `Film` must have `language`, `actors` and `categories`; `Actor` and `Category` must have `films`.
2. Write these 3 queries with the ORM, run them with `echo=True`, and compare the SQL the ORM generates with the handwritten SQL below:

   ```sql
   -- Q1: number of films per category, most films first
   SELECT c.name, count(*) AS films
   FROM category c JOIN film_category fc ON fc.category_id = c.category_id
   GROUP BY c.category_id, c.name
   ORDER BY films DESC, c.name;

   -- Q2: films longer than the average film
   SELECT f.film_id, f.title, f.length
   FROM film f
   WHERE f.length > (SELECT avg(length) FROM film)
   ORDER BY f.length DESC, f.film_id;

   -- Q3: the 10 actors with most films
   SELECT a.actor_id, a.first_name, a.last_name, count(*) AS films
   FROM actor a JOIN film_actor fa ON fa.actor_id = a.actor_id
   GROUP BY a.actor_id
   ORDER BY films DESC, a.actor_id
   LIMIT 10;
   ```

3. Create an N+1 on purpose: load the first 100 films by `film_id` and print each title with the names of its actors through `film.actors`. Count the `SELECT` statements. Fix it with eager loading and count again, in a new session.

**Deliverables.**

- `models.py`, `queries.py`, `n_plus_one.py`, `pyproject.toml`.
- `README.md` with the commands to run each script, the handwritten and generated SQL of each query side by side with the differences you notice, and the number of queries before and after the fix.

**Done when.** The 3 ORM queries return the same rows as the handwritten SQL, the N+1 version runs 101 queries, and the fixed version runs at most 2.

## Challenge (opcional, em `challenge/`)

Enunciado completo em [challenge/README.md](../challenge/README.md).

## Checklist

- [x] `models.py`: 6 tables mapped with relationships
- [x] `queries.py`: Q1-Q3 with the ORM, generated SQL vs handwritten SQL
- [x] `n_plus_one.py`: 101 queries before, at most 2 after

## Resolução

Ficheiros entregues:

- [models.py](models.py): os 6 modelos com `Mapped` e `mapped_column`. `FilmActor` e `FilmCategory` mapeiam as tabelas de ligação (as duas chaves, que formam a chave primária, e `last_update`). As relações muitos-para-muitos usam essas tabelas como `secondary`. `Film` tem `language`, `actors` e `categories`; `Actor` e `Category` têm `films`.
- [queries.py](queries.py): Q1–Q3 com o ORM. Corre cada uma com `echo=True`, corre também o SQL escrito à mão e diz se as linhas são iguais.
- [n_plus_one.py](n_plus_one.py): o N+1 de propósito e a correção com `selectinload`, cada versão na sua sessão. Conta os `SELECT` com o evento `before_cursor_execute`.
- [pyproject.toml](pyproject.toml) e `uv.lock`.

`Film` só mapeia as colunas que o exercício usa. As colunas `release_year` (domínio `year`), `rating` (enum `mpaa_rating`), `special_features` e `fulltext` ficaram de fora porque nenhuma query precisa delas.

### Como correr

```bash
# a partir da raiz do repositório
./scripts/create-db.sh ex11 --pagila --reset
cd exercises/11-orm/exercise
uv sync
uv run python queries.py
uv run python n_plus_one.py
```

O URL por omissão é `postgresql+psycopg:///ex11`: o host, o utilizador e a password vêm de `PGHOST`, `PGUSER` e `PGPASSWORD`. Para outro destino, usar `EX11_DATABASE_URL`.

### Q1–Q3: linhas

```
Q1: 16 rows from the ORM, 16 from the SQL, same rows
Q2: 489 rows from the ORM, 489 from the SQL, same rows
Q3: 10 rows from the ORM, 10 from the SQL, same rows
```

### Q1: filmes por categoria

| Escrito à mão | Gerado pelo ORM |
|---------------|-----------------|
| <pre>SELECT c.name, count(*) AS films<br>FROM category c<br>JOIN film_category fc ON fc.category_id = c.category_id<br>GROUP BY c.category_id, c.name<br>ORDER BY films DESC, c.name;</pre> | <pre>SELECT category.name, count(*) AS films<br>FROM category<br>JOIN film_category ON film_category.category_id = category.category_id<br>GROUP BY category.category_id, category.name<br>ORDER BY films DESC, category.name</pre> |

- O ORM não usa aliases: escreve o nome completo das tabelas (`category.name` em vez de `c.name`).
- O `count(*) AS films` vem de `func.count().label("films")`, e o `ORDER BY films DESC` refere-se ao mesmo label.
- O `JOIN` com `film_category` tem de ter o `ON` explícito, porque a query junta o modelo `FilmCategory` e não segue uma relação. Com `.join(Category.films)` o ORM juntava também `film`, o que é um join a mais.

### Q2: filmes mais longos do que a média

| Escrito à mão | Gerado pelo ORM |
|---------------|-----------------|
| <pre>SELECT f.film_id, f.title, f.length<br>FROM film f<br>WHERE f.length > (SELECT avg(length) FROM film)<br>ORDER BY f.length DESC, f.film_id;</pre> | <pre>SELECT film.film_id, film.title, film.length<br>FROM film<br>WHERE film.length > (SELECT avg(film.length) AS avg_1<br>  FROM film)<br>ORDER BY film.length DESC, film.film_id</pre> |

- A subquery vem de `select(func.avg(Film.length)).scalar_subquery()`.
- O ORM dá à coluna da subquery um nome automático (`AS avg_1`), que não serve para nada numa subquery escalar.
- Dentro da subquery, `film.length` refere-se ao `film` interior. Não há correlação com o `film` exterior: o ORM só correlaciona se a subquery referir uma tabela que exista apenas fora dela. Aqui as duas são `film`, e o SQL gerado é igual ao escrito à mão.

### Q3: os 10 atores com mais filmes

| Escrito à mão | Gerado pelo ORM |
|---------------|-----------------|
| <pre>SELECT a.actor_id, a.first_name, a.last_name, count(*) AS films<br>FROM actor a<br>JOIN film_actor fa ON fa.actor_id = a.actor_id<br>GROUP BY a.actor_id<br>ORDER BY films DESC, a.actor_id<br>LIMIT 10;</pre> | <pre>SELECT actor.actor_id, actor.first_name, actor.last_name, count(*) AS films<br>FROM actor<br>JOIN film_actor ON film_actor.actor_id = actor.actor_id<br>GROUP BY actor.actor_id<br>ORDER BY films DESC, actor.actor_id<br>LIMIT %(param_1)s::INTEGER<br>-- {'param_1': 10}</pre> |

- O `LIMIT` passa a ser um parâmetro (`%(param_1)s::INTEGER`, com o valor `10` à parte). Assim, a mesma query com outro limite reaproveita a cache de compilação do SQLAlchemy.
- O `GROUP BY actor.actor_id` só funciona porque `actor_id` é a chave primária. O PostgreSQL aceita então `first_name` e `last_name` no `SELECT` sem estarem no `GROUP BY`, tanto no SQL à mão como no gerado.

### N+1: número de queries

```
$ uv run python n_plus_one.py
ACADEMY DINOSAUR: PENELOPE GUINESS, CHRISTIAN GABLE, LUCILLE TRACY, ...
...
--- N+1 (lazy loading): 101 SELECT statements
...
--- fixed (selectinload): 2 SELECT statements

before: 101 queries, after: 2 queries
```

Antes (lazy loading), 1 query para os filmes e 1 por filme quando se lê `film.actors`:

```sql
SELECT film.film_id, film.title, film.description, film.language_id, film.length, film.last_update
FROM film ORDER BY film.film_id LIMIT %(param_1)s::INTEGER          -- {'param_1': 100}

SELECT actor.actor_id, actor.first_name, actor.last_name, actor.last_update
FROM actor, film_actor
WHERE %(param_1)s::INTEGER = film_actor.film_id AND actor.actor_id = film_actor.actor_id
                                                                    -- {'param_1': 1}, depois 2, 3, ... 100
```

Depois (`.options(selectinload(Film.actors))`), a mesma query dos filmes e 1 query para os atores de todos eles:

```sql
SELECT film_actor.film_id, actor.actor_id, actor.first_name, actor.last_name, actor.last_update
FROM film_actor JOIN actor ON actor.actor_id = film_actor.actor_id
WHERE film_actor.film_id IN (%(primary_keys_1)s::INTEGER, ..., %(primary_keys_100)s::INTEGER)
```

| Versão | `SELECT` |
|--------|----------|
| Lazy loading (N+1) | 101 |
| `selectinload(Film.actors)` | 2 |

Escolhi `selectinload` e não `joinedload` porque `actors` é uma coleção. Com `joinedload` seria 1 query só, mas cada filme vinha repetido uma vez por ator (cerca de 550 linhas para 100 filmes). O `LIMIT 100` também teria de passar para uma subquery, para limitar filmes e não linhas do join.
