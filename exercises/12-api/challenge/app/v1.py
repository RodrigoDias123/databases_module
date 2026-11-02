"""Version 1 of the API, on port 8001: the code from before the rename, which uses customer.email.

It uses the models of that version (app/models_v1.py). It works before the expand migration and
after it, and stops working after the contract migration.
"""
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app import models_v1
from app.db import get_session
from app.models_v1 import Customer
from app.rentals import rentals_router
from app.schemas import CustomerOut, EmailIn

app = FastAPI(title="Challenge 12: API version 1 (customer.email)")
app.include_router(rentals_router(models_v1))

SessionDep = Annotated[Session, Depends(get_session)]


def to_out(customer: Customer) -> CustomerOut:
    return CustomerOut(
        customer_id=customer.customer_id,
        first_name=customer.first_name,
        last_name=customer.last_name,
        email=customer.email,
    )


@app.get("/customers/{customer_id}")
def get_customer(customer_id: int, session: SessionDep) -> CustomerOut:
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(404, "customer not found")
    return to_out(customer)


@app.put("/customers/{customer_id}/email")
def set_email(customer_id: int, body: EmailIn, session: SessionDep) -> CustomerOut:
    with session.begin():
        customer = session.get(Customer, customer_id)
        if customer is None:
            raise HTTPException(404, "customer not found")
        customer.email = body.email
    return to_out(customer)
