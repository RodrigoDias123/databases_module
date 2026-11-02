"""Requests of tasks 3 and 4 against the two versions of the API.

    uv run python check_versions.py expand     # after 0004, with version 1 and version 2 running
    uv run python check_versions.py contract   # after 0005, with only version 2 running

After each write it also reads the row from the database, to show what is in each column.
Both modes also call the rental endpoints, and return the rentals they open, so the script can
run again on the same database.
"""
import os
import sys

import httpx
from sqlalchemy import text

from models import make_engine

V1_URL = os.environ.get("CH12_V1_URL", "http://127.0.0.1:8001")
V2_URL = os.environ.get("CH12_V2_URL", "http://127.0.0.1:8002")
CUSTOMER_ID = 1
# Film 7 has 2 copies in store 1.
RENTAL = {"film_id": 7, "store_id": 1, "staff_id": 6}
OVERDUE = "/rentals/overdue?as_of=2026-07-31"

engine = make_engine()
failures = 0


def check(label: str, ok: bool) -> None:
    global failures
    failures += not ok
    print(f"  {'OK  ' if ok else 'FAIL'} {label}")


def email_columns() -> list[str]:
    with engine.connect() as conn:
        return list(conn.scalars(text(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_name = 'customer' AND column_name LIKE 'email%' ORDER BY column_name"
        )))


def show_row() -> None:
    columns = email_columns()
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT {', '.join(columns)} FROM customer WHERE customer_id = :id"),
            {"id": CUSTOMER_ID},
        ).one()
    print("  database:", ", ".join(f"{c} = {v!r}" for c, v in zip(columns, row)))


def put(url: str, email: str) -> dict:
    r = httpx.put(f"{url}/customers/{CUSTOMER_ID}/email", json={"email": email})
    print(f"PUT {url}/customers/{CUSTOMER_ID}/email {{'email': {email!r}}} -> {r.status_code} {r.json()}")
    r.raise_for_status()
    return r.json()


def get(url: str) -> dict:
    r = httpx.get(f"{url}/customers/{CUSTOMER_ID}")
    print(f"GET {url}/customers/{CUSTOMER_ID} -> {r.status_code} {r.json()}")
    r.raise_for_status()
    return r.json()


def post(url: str, path: str, body: dict | None = None) -> httpx.Response:
    r = httpx.post(f"{url}{path}", json=body)
    print(f"POST {url}{path}{f' {body}' if body else ''} -> {r.status_code} {r.json()}")
    return r


def overdue(url: str) -> list:
    r = httpx.get(f"{url}{OVERDUE}")
    r.raise_for_status()
    print(f"GET {url}{OVERDUE} -> {r.status_code}, {len(r.json())} items")
    return r.json()


def rent(url: str, customer_id: int) -> httpx.Response:
    return post(url, "/rentals", {"customer_id": customer_id, **RENTAL})


def expand() -> None:
    print("--- both versions read the same email")
    check("version 1 and version 2 return the same customer", get(V1_URL) == get(V2_URL))

    print("\n--- write through version 1 (email), read through version 2 (email_address)")
    put(V1_URL, "mary.smith.v1@example.com")
    show_row()
    check("version 2 sees the change", get(V2_URL)["email"] == "mary.smith.v1@example.com")

    print("\n--- write through version 2 (email_address), read through version 1 (email)")
    put(V2_URL, "mary.smith.v2@example.com")
    show_row()
    check("version 1 sees the change", get(V1_URL)["email"] == "mary.smith.v2@example.com")

    print("\n--- rentals: both versions work on the same rows")
    v1_overdue, v2_overdue = overdue(V1_URL), overdue(V2_URL)
    check("same overdue list, 229 items", v1_overdue == v2_overdue and len(v1_overdue) == 229)

    a, b = rent(V1_URL, 2), rent(V2_URL, 3)
    check(
        "one copy rented through each version",
        a.status_code == b.status_code == 201
        and a.json()["inventory_id"] != b.json()["inventory_id"],
    )
    check("no copy left for version 1", rent(V1_URL, 4).status_code == 409)

    a_id, b_id = a.json()["rental_id"], b.json()["rental_id"]
    r = post(V2_URL, f"/rentals/{a_id}/return")
    check("version 2 returns the rental opened by version 1", r.status_code == 200)
    r = post(V1_URL, f"/rentals/{a_id}/return")
    check("version 1 sees it returned", r.status_code == 409)
    r = post(V1_URL, f"/rentals/{b_id}/return")
    check("version 1 returns the rental opened by version 2", r.status_code == 200)


def contract() -> None:
    print("--- version 1 is stopped")
    try:
        httpx.get(f"{V1_URL}/customers/{CUSTOMER_ID}")
        check("version 1 does not answer", False)
    except httpx.ConnectError as e:
        print(f"GET {V1_URL}/customers/{CUSTOMER_ID} -> {e}")
        check("version 1 does not answer", True)

    print("\n--- customer.email no longer exists")
    columns = email_columns()
    print("  email columns of customer:", columns)
    check("only email_address is left", columns == ["email_address"])

    print("\n--- version 2 still works")
    put(V2_URL, "mary.smith.contract@example.com")
    show_row()
    check("version 2 reads its own change", get(V2_URL)["email"] == "mary.smith.contract@example.com")

    print("\n--- rentals through version 2")
    check("overdue list has 229 items", len(overdue(V2_URL)) == 229)
    r = rent(V2_URL, 2)
    check("rent a copy", r.status_code == 201)
    r = post(V2_URL, f"/rentals/{r.json()['rental_id']}/return")
    check("return it", r.status_code == 200)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("expand", "contract"):
        sys.exit(__doc__)
    {"expand": expand, "contract": contract}[mode]()
    print("\nOK" if failures == 0 else f"\n{failures} check(s) failed")
    sys.exit(1 if failures else 0)
