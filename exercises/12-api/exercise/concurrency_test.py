"""5 simultaneous POST /rentals for film 7 in store 1 (customers 1 to 5, staff 6).

Film 7 has exactly 2 copies in store 1 (inventory 32 and 33), both available on a fresh copy
of the database. Expected: two 201 with two different inventory_id, and three 409.

Needs the API running (uvicorn app.main:app). Run it on a fresh copy: the two rentals it
creates stay open, so a second run gets five 409.
"""
import asyncio
import os
import sys
from collections import Counter

import httpx

API_URL = os.environ.get("EX12_API_URL", "http://127.0.0.1:8000")
FILM_ID, STORE_ID, STAFF_ID = 7, 1, 6
CUSTOMERS = range(1, 6)


async def main() -> int:
    async with httpx.AsyncClient(base_url=API_URL, timeout=30) as client:
        # gather() sends the 5 requests at the same time, each on its own connection.
        responses = await asyncio.gather(
            *(
                client.post(
                    "/rentals",
                    json={
                        "customer_id": customer_id,
                        "film_id": FILM_ID,
                        "store_id": STORE_ID,
                        "staff_id": STAFF_ID,
                    },
                )
                for customer_id in CUSTOMERS
            )
        )

    for customer_id, response in zip(CUSTOMERS, responses):
        print(f"customer {customer_id}: {response.status_code} {response.json()}")

    statuses = Counter(r.status_code for r in responses)
    copies = {r.json()["inventory_id"] for r in responses if r.status_code == 201}
    print(f"\n201: {statuses[201]}, 409: {statuses[409]}, inventory_id of the 201s: {sorted(copies)}")

    ok = statuses == Counter({201: 2, 409: 3}) and len(copies) == 2
    print("OK" if ok else "FAILED: expected two 201 with different inventory_id and three 409")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
