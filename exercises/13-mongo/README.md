# Exercício 13: MongoDB I, documents, CRUD and validation

## Enunciado

Folder: `exercises/13-mongo/`

1. A Python script that reads Pagila and writes the collections `films` (actors and category embedded) and `customers` (last 10 rentals embedded, the rest referenced). Justify your choices.
2. 8 `find`/`update` operations with their expected results.
3. `$jsonSchema` on `films`, and an invalid document being rejected.
4. One index with `explain` before and after.

Marked 2 when all four points are done, with justifications.

Group project: design the report documents for your scenario (in scenario C, also the events) and their `$jsonSchema` validation.

## Challenge (obrigatório, em `challenge/`)

Model each customer's full rental history with the **bucket pattern**: documents of at most 50 rentals each, with `customer_id`, a sequence number and a count. Write the insert logic that adds a rental to the current bucket or opens a new one atomically (a single `updateOne` with upsert and a filter on the count). Compare the size and read time of "last 20 rentals" against a single document with every rental embedded.

## Checklist

- [ ] Python script: Pagila -> `films` (actors and category embedded) and `customers` (last 10 rentals embedded, rest referenced), with justification
- [ ] 8 find/update operations with expected results
- [ ] $jsonSchema on `films` and an invalid document rejected
- [ ] One index with explain before and after
