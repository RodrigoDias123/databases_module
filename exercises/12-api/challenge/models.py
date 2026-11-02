"""SQLAlchemy 2.0 models for 5 Pagila tables: customer, film, inventory, rental, staff.

Every column and index of these tables is mapped, so `alembic revision --autogenerate` finds
nothing to change. Foreign keys are declared only between these 5 tables: the ones to store,
address and language (not mapped) stay in the database, and migrations/env.py ignores them.
The models describe the schema at `alembic head`: `customer.loyalty_points` (0002), the
partial index `rental_one_open_per_copy` (0003) and `customer.email_address`, which replaces
`customer.email` (0004 expand, 0005 contract). Version 2 of the API uses these models.
"""
import os
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    Text,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import DOMAIN, ENUM, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# psycopg reads the host, user and password from PGHOST, PGUSER and PGPASSWORD.
DATABASE_URL = os.environ.get("CH12_DATABASE_URL", "postgresql+psycopg:///ch12")

# Types that already exist in Pagila: never created or dropped from here.
Year = DOMAIN("year", Integer, check="VALUE >= 1901 AND VALUE <= 2155", create_type=False)
MpaaRating = ENUM("G", "PG", "PG-13", "R", "NC-17", name="mpaa_rating", create_type=False)

TIMESTAMPTZ = DateTime(timezone=True)


class Base(DeclarativeBase):
    type_annotation_map = {str: Text, datetime: TIMESTAMPTZ}


class Customer(Base):
    __tablename__ = "customer"
    __table_args__ = (
        Index("idx_fk_address_id", "address_id"),
        Index("idx_fk_store_id", "store_id"),
        Index("idx_last_name", "last_name"),
        Index("customer_uuid_key", "uuid", unique=True),
    )

    customer_id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int]
    first_name: Mapped[str]
    last_name: Mapped[str]
    email_address: Mapped[str | None]
    address_id: Mapped[int]
    activebool: Mapped[bool] = mapped_column(server_default=text("true"))
    create_date: Mapped[date] = mapped_column(server_default=text("CURRENT_DATE"))
    last_update: Mapped[datetime | None] = mapped_column(server_default=text("now()"))
    active: Mapped[int | None]
    uuid: Mapped[UUID] = mapped_column(server_default=text("uuidv7()"))
    loyalty_points: Mapped[int] = mapped_column(server_default=text("0"))

    rentals: Mapped[list["Rental"]] = relationship(back_populates="customer")


class Staff(Base):
    __tablename__ = "staff"

    staff_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    address_id: Mapped[int]
    email: Mapped[str | None]
    store_id: Mapped[int]
    active: Mapped[bool] = mapped_column(server_default=text("true"))
    username: Mapped[str]
    password: Mapped[str | None]
    last_update: Mapped[datetime] = mapped_column(server_default=text("now()"))
    picture: Mapped[bytes | None] = mapped_column(LargeBinary)


class Film(Base):
    __tablename__ = "film"
    __table_args__ = (
        Index("film_fulltext_idx", "fulltext", postgresql_using="gist"),
        Index("idx_fk_language_id", "language_id"),
        Index("idx_fk_original_language_id", "original_language_id"),
        Index("idx_title", "title"),
    )

    film_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[str | None]
    release_year: Mapped[int | None] = mapped_column(Year)
    language_id: Mapped[int]
    original_language_id: Mapped[int | None]
    rental_duration: Mapped[int] = mapped_column(SmallInteger, server_default=text("3"))
    rental_rate: Mapped[Decimal] = mapped_column(Numeric(4, 2), server_default=text("4.99"))
    length: Mapped[int | None] = mapped_column(SmallInteger)
    replacement_cost: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default=text("19.99"))
    rating: Mapped[str | None] = mapped_column(MpaaRating, server_default=text("'G'::mpaa_rating"))
    last_update: Mapped[datetime] = mapped_column(server_default=text("now()"))
    special_features: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    # Filled by the film_fulltext_trigger trigger.
    fulltext: Mapped[str] = mapped_column(TSVECTOR)


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (Index("idx_store_id_film_id", "store_id", "film_id"),)

    inventory_id: Mapped[int] = mapped_column(primary_key=True)
    film_id: Mapped[int] = mapped_column(
        ForeignKey("film.film_id", onupdate="CASCADE", ondelete="RESTRICT")
    )
    store_id: Mapped[int]
    last_update: Mapped[datetime] = mapped_column(server_default=text("now()"))

    film: Mapped[Film] = relationship()


class Rental(Base):
    __tablename__ = "rental"
    __table_args__ = (
        Index("idx_fk_inventory_id", "inventory_id"),
        Index(
            "idx_unq_rental_rental_date_inventory_id_customer_id",
            "rental_date", "inventory_id", "customer_id",
            unique=True,
        ),
        Index("rental_uuid_key", "uuid", unique=True),
        # 0003: at most one open rental per copy.
        Index(
            "rental_one_open_per_copy",
            "inventory_id",
            unique=True,
            postgresql_where=text("return_date IS NULL"),
        ),
    )

    rental_id: Mapped[int] = mapped_column(primary_key=True)
    rental_date: Mapped[datetime]
    inventory_id: Mapped[int] = mapped_column(
        ForeignKey("inventory.inventory_id", onupdate="CASCADE", ondelete="RESTRICT")
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customer.customer_id", onupdate="CASCADE", ondelete="RESTRICT")
    )
    return_date: Mapped[datetime | None]
    staff_id: Mapped[int] = mapped_column(
        ForeignKey("staff.staff_id", onupdate="CASCADE", ondelete="RESTRICT")
    )
    last_update: Mapped[datetime] = mapped_column(server_default=text("now()"))
    uuid: Mapped[UUID] = mapped_column(server_default=text("uuidv7()"))

    customer: Mapped[Customer] = relationship(back_populates="rentals")
    inventory: Mapped[Inventory] = relationship()
    staff: Mapped[Staff] = relationship()


def make_engine(**kwargs):
    return create_engine(DATABASE_URL, **kwargs)
