# Challenge 13: MongoDB I, documents, CRUD and validation

Opcional.

## Enunciado

Model each customer's full rental history with the **bucket pattern**: documents of at most 50 rentals each, with `customer_id`, a sequence number and a count. Write the insert logic that adds a rental to the current bucket or opens a new one atomically (a single `updateOne` with upsert and a filter on the count). Compare the size and read time of "last 20 rentals" against a single document with every rental embedded.
