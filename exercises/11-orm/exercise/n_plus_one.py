"""The first 100 films with their actors: an N+1 on purpose, then the fix with eager loading."""
from sqlalchemy import event, select
from sqlalchemy.orm import Session, selectinload

from models import Film, make_engine

engine = make_engine()
selects = 0


@event.listens_for(engine, "before_cursor_execute")
def count_selects(conn, cursor, statement, parameters, context, executemany):
    global selects
    if statement.lstrip().upper().startswith("SELECT"):
        selects += 1


def print_films(stmt):
    with Session(engine) as session:
        for film in session.scalars(stmt):
            names = ", ".join(f"{a.first_name} {a.last_name}" for a in film.actors)
            print(f"{film.title}: {names}")


def run(label, stmt):
    global selects
    selects = 0
    print_films(stmt)
    print(f"--- {label}: {selects} SELECT statements\n")
    return selects


def main():
    first_100 = select(Film).order_by(Film.film_id).limit(100)
    before = run("N+1 (lazy loading)", first_100)
    after = run("fixed (selectinload)", first_100.options(selectinload(Film.actors)))
    print(f"before: {before} queries, after: {after} queries")


if __name__ == "__main__":
    main()
