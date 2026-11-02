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

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [ ] `models.py`: 6 tables mapped with relationships
- [ ] `queries.py`: Q1-Q3 with the ORM, generated SQL vs handwritten SQL
- [ ] `n_plus_one.py`: 101 queries before, at most 2 after
