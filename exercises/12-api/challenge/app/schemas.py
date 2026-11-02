"""The HTTP contract, the same in both versions: the column is renamed, the API is not."""
from pydantic import BaseModel


class EmailIn(BaseModel):
    email: str


class CustomerOut(BaseModel):
    customer_id: int
    first_name: str
    last_name: str
    email: str | None
