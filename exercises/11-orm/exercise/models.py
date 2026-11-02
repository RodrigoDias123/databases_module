"""SQLAlchemy 2.0 models for 6 Pagila tables: film, language, actor, film_actor, category, film_category."""
import os
from datetime import datetime

from sqlalchemy import ForeignKey, SmallInteger, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# psycopg reads the host, user and password from PGHOST, PGUSER and PGPASSWORD.
DATABASE_URL = os.environ.get("EX11_DATABASE_URL", "postgresql+psycopg:///ex11")


class Base(DeclarativeBase):
    pass


class FilmActor(Base):
    __tablename__ = "film_actor"

    actor_id: Mapped[int] = mapped_column(ForeignKey("actor.actor_id"), primary_key=True)
    film_id: Mapped[int] = mapped_column(ForeignKey("film.film_id"), primary_key=True)
    last_update: Mapped[datetime]


class FilmCategory(Base):
    __tablename__ = "film_category"

    film_id: Mapped[int] = mapped_column(ForeignKey("film.film_id"), primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.category_id"), primary_key=True)
    last_update: Mapped[datetime]


class Language(Base):
    __tablename__ = "language"

    language_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    last_update: Mapped[datetime]

    films: Mapped[list["Film"]] = relationship(
        back_populates="language", foreign_keys="Film.language_id"
    )


class Film(Base):
    __tablename__ = "film"

    film_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[str | None]
    language_id: Mapped[int] = mapped_column(ForeignKey("language.language_id"))
    length: Mapped[int | None] = mapped_column(SmallInteger)
    last_update: Mapped[datetime]

    language: Mapped[Language] = relationship(back_populates="films", foreign_keys=[language_id])
    actors: Mapped[list["Actor"]] = relationship(secondary="film_actor", back_populates="films")
    categories: Mapped[list["Category"]] = relationship(
        secondary="film_category", back_populates="films"
    )


class Actor(Base):
    __tablename__ = "actor"

    actor_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    last_update: Mapped[datetime]

    films: Mapped[list[Film]] = relationship(secondary="film_actor", back_populates="actors")


class Category(Base):
    __tablename__ = "category"

    category_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    last_update: Mapped[datetime]

    films: Mapped[list[Film]] = relationship(secondary="film_category", back_populates="categories")


def make_engine(**kwargs):
    return create_engine(DATABASE_URL, **kwargs)
