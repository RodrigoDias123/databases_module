# Challenge 13: MongoDB I, documents, CRUD and validation

Opcional.

## Enunciado

Folder: `exercises/13-mongo/challenge/`

**Goal.** Store a history that grows without limit with the bucket pattern, and measure the difference.

**Starting point.** The `rentals` collection of the exercise above (or `load.py` run again).

**Tasks.**

1. Design the collection `rental_buckets`: each document holds at most 50 rentals of one customer, with `customer_id`, a sequence number `seq`, a `count` and an array `rentals`.
2. Write `add_rental(customer_id, rental)` that adds a rental to the customer's open bucket, or opens a new one, with a single `updateOne` with `upsert: true` and a filter on `count`. Explain what makes it safe when two calls for the same customer run at the same time, and what you need (for example a unique index) to keep it safe.
3. Fill `rental_buckets` from `rentals` with `add_rental`, in `rental_date` order.
4. Build a second collection `rental_history` with one document per customer embedding every rental.
5. For customer 380 (97 rentals, the most in Pagila), compare the document sizes (`Object.bsonsize`) and the time to read the 20 most recent rentals from each collection.

**Deliverables.**

- `buckets.py` (or `.js`) with the functions and the loading code.
- `README.md` with the design, the explanation of task 2, and the sizes and times of task 5.

**Done when.** No bucket has more than 50 rentals, customer 380 has two buckets (50 and 47 rentals), and the README explains when the bucket pattern pays off.
