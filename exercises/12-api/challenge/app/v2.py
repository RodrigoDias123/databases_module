"""Version 2 of the API, on port 8002: uses customer.email_address, through models.py.

Deployed after the expand migration, and the only version left after the contract migration.
"""
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

import models
from app.db import get_session
from app.rentals import rentals_router
from app.schemas import CustomerOut, EmailIn
from models import Customer

app = FastAPI(title="Challenge 12: API version 2 (customer.email_address)")
app.include_router(rentals_router(models))

SessionDep = Annotated[Session, Depends(get_session)]


def to_out(customer: Customer) -> CustomerOut:
    return CustomerOut(
        customer_id=customer.customer_id,
        first_name=customer.first_name,
        last_name=customer.last_name,
        email=customer.email_address,
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
        customer.email_address = body.email
    return to_out(customer)
