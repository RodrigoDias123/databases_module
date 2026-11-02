"""Q1-Q3 with the ORM, run with echo=True and checked against the handwritten SQL."""
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from models import Actor, Category, Film, FilmActor, FilmCategory, make_engine

HANDWRITTEN = {
    "Q1": """
        SELECT c.name, count(*) AS films
        FROM category c JOIN film_category fc ON fc.category_id = c.category_id
        GROUP BY c.category_id, c.name
        ORDER BY films DESC, c.name
    """,
    "Q2": """
        SELECT f.film_id, f.title, f.length
        FROM film f
        WHERE f.length > (SELECT avg(length) FROM film)
        ORDER BY f.length DESC, f.film_id
    """,
    "Q3": """
        SELECT a.actor_id, a.first_name, a.last_name, count(*) AS films
        FROM actor a JOIN film_actor fa ON fa.actor_id = a.actor_id
        GROUP BY a.actor_id
        ORDER BY films DESC, a.actor_id
        LIMIT 10
    """,
}


def q1_films_per_category():
    films = func.count().label("films")
    return (
        select(Category.name, films)
        .join(FilmCategory, FilmCategory.category_id == Category.category_id)
        .group_by(Category.category_id, Category.name)
        .order_by(films.desc(), Category.name)
    )


def q2_films_longer_than_average():
    average = select(func.avg(Film.length)).scalar_subquery()
    return (
        select(Film.film_id, Film.title, Film.length)
        .where(Film.length > average)
        .order_by(Film.length.desc(), Film.film_id)
    )


def q3_actors_with_most_films():
    films = func.count().label("films")
    return (
        select(Actor.actor_id, Actor.first_name, Actor.last_name, films)
        .join(FilmActor, FilmActor.actor_id == Actor.actor_id)
        .group_by(Actor.actor_id)
        .order_by(films.desc(), Actor.actor_id)
        .limit(10)
    )


ORM = {"Q1": q1_films_per_category, "Q2": q2_films_longer_than_average, "Q3": q3_actors_with_most_films}


def main():
    engine = make_engine(echo=True)
    with Session(engine) as session:
        for name, query in ORM.items():
            print(f"\n===== {name} =====")
            orm_rows = [tuple(row) for row in session.execute(query())]
            sql_rows = [tuple(row) for row in session.execute(text(HANDWRITTEN[name]))]
            same = "same rows" if orm_rows == sql_rows else "DIFFERENT ROWS"
            print(f"{name}: {len(orm_rows)} rows from the ORM, {len(sql_rows)} from the SQL, {same}")
            for row in orm_rows[:3]:
                print("  ", row)


if __name__ == "__main__":
    main()
