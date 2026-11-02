import logging
from datetime import date, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import exists, func, literal_column, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager

from app.db import get_session
from models import Customer, Film, Inventory, Rental, Staff

log = logging.getLogger("uvicorn.error")

app = FastAPI(title="Exercise 12: rentals API")

SessionDep = Annotated[Session, Depends(get_session)]

# After the first attempt, POST /rentals tries again at most this many times.
MAX_RETRIES = 3


# --- POST /rentals --------------------------------------------------------------------------

class RentalIn(BaseModel):
    customer_id: int
    film_id: int
    store_id: int
    staff_id: int


class RentalOut(BaseModel):
    rental_id: int
    inventory_id: int


class CopyTaken(Exception):
    """Another transaction opened a rental on the same copy between our SELECT and our INSERT."""


def rent_once(session: Session, body: RentalIn) -> RentalOut:
    """One attempt, in one transaction: pick a free copy, lock it, insert the rental."""
    with session.begin():
        if session.get(Customer, body.customer_id) is None:
            raise HTTPException(404, "customer not found")
        if session.get(Film, body.film_id) is None:
            raise HTTPException(404, "film not found")
        if session.get(Staff, body.staff_id) is None:
            raise HTTPException(404, "staff not found")

        open_rental = exists().where(
            Rental.inventory_id == Inventory.inventory_id, Rental.return_date.is_(None)
        )
        # skip_locked: a copy locked by a concurrent request is skipped, not waited for.
        # Two requests therefore get two different copies instead of queueing on the same one.
        inventory_id = session.scalar(
            select(Inventory.inventory_id)
            .where(
                Inventory.film_id == body.film_id,
                Inventory.store_id == body.store_id,
                ~open_rental,
            )
            .order_by(Inventory.inventory_id)
            .limit(1)
            .with_for_update(skip_locked=True, of=Inventory)
        )
        if inventory_id is None:
            raise HTTPException(409, "no copy of this film is available in this store")

        rental = Rental(
            rental_date=func.now(),
            inventory_id=inventory_id,
            customer_id=body.customer_id,
            staff_id=body.staff_id,
        )
        session.add(rental)
        try:
            session.flush()
        except IntegrityError as e:
            if e.orig.diag.constraint_name == "rental_one_open_per_copy":
                raise CopyTaken from e
            raise
        return RentalOut(rental_id=rental.rental_id, inventory_id=inventory_id)


@app.post("/rentals", status_code=201)
def create_rental(body: RentalIn, session: SessionDep) -> RentalOut:
    for attempt in range(1 + MAX_RETRIES):
        try:
            return rent_once(session, body)
        except CopyTaken:
            log.info("POST /rentals: copy taken by another request, attempt %d", attempt + 1)
    raise HTTPException(409, "no copy of this film is available in this store")


# --- POST /rentals/{rental_id}/return -------------------------------------------------------

class ReturnOut(BaseModel):
    rental_id: int
    return_date: datetime


@app.post("/rentals/{rental_id}/return")
def return_rental(rental_id: int, session: SessionDep) -> ReturnOut:
    with session.begin():
        # FOR UPDATE: two returns of the same rental queue here, and the second one sees the
        # return_date written by the first and gets a 409.
        rental = session.scalar(
            select(Rental).where(Rental.rental_id == rental_id).with_for_update()
        )
        if rental is None:
            raise HTTPException(404, "rental not found")
        if rental.return_date is not None:
            raise HTTPException(409, "rental already returned")
        rental.return_date = session.scalar(select(func.now()))
    return ReturnOut(rental_id=rental.rental_id, return_date=rental.return_date)


# --- GET /rentals/overdue -------------------------------------------------------------------

class CustomerOut(BaseModel):
    customer_id: int
    first_name: str
    last_name: str


class FilmOut(BaseModel):
    film_id: int
    title: str


class OverdueOut(BaseModel):
    rental_id: int
    rental_date: datetime
    due_date: datetime
    customer: CustomerOut
    film: FilmOut


@app.get("/rentals/overdue")
def overdue_rentals(session: SessionDep, as_of: Annotated[date, Query()]) -> list[OverdueOut]:
    """Open rentals past their due date, in one SELECT.

    The joins to customer, inventory and film are in the query anyway (the due date needs
    film.rental_duration), and contains_eager fills Rental.customer and Rental.inventory.film
    from them. Without it, reading rental.customer and rental.inventory.film would run up to 3
    extra SELECTs per rental: an N+1.
    """
    due_date = (
        Rental.rental_date + Film.rental_duration * literal_column("interval '1 day'")
    ).label("due_date")
    rows = session.execute(
        select(Rental, due_date)
        .join(Rental.customer)
        .join(Rental.inventory)
        .join(Inventory.film)
        .where(Rental.return_date.is_(None), due_date < as_of)
        .order_by(Rental.rental_date, Rental.rental_id)
        .options(
            contains_eager(Rental.customer),
            contains_eager(Rental.inventory).contains_eager(Inventory.film),
        )
    ).all()
    return [
        OverdueOut(
            rental_id=rental.rental_id,
            rental_date=rental.rental_date,
            due_date=due,
            customer=CustomerOut.model_validate(rental.customer, from_attributes=True),
            film=FilmOut.model_validate(rental.inventory.film, from_attributes=True),
        )
        for rental, due in rows
    ]
