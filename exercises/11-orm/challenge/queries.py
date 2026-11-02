"""The query under test: the first 100 films with their actors and categories."""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import Film


def films_with_actors_and_categories(session: Session, limit: int = 100) -> list[dict]:
    stmt = (
        select(Film)
        .options(selectinload(Film.actors), selectinload(Film.categories))
        .order_by(Film.film_id)
        .limit(limit)
    )
    return [
        {
            "title": film.title,
            "actors": [f"{a.first_name} {a.last_name}" for a in film.actors],
            "categories": [c.name for c in film.categories],
        }
        for film in session.scalars(stmt)
    ]
