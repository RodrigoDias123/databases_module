# Exercício 13: MongoDB I, documents, CRUD and validation

## Enunciado

Folder: `exercises/13-mongo/exercise/`

**Goal.** Turn relational data into documents, choosing what to embed and what to reference, and query, validate and index them.

**Starting point.** A fresh copy of Pagila (`./scripts/create-db.sh ex13 --pagila --reset`), the MongoDB database `pagila_docs`, and a uv project:

```bash
uv init --bare
uv add pymongo "psycopg[binary]"
```

The script reads `DATABASE_URL` and `MONGO_URL` from the environment (see `.env.example`). The collections must have these shapes. In this version of Pagila a film can belong to more than one category, so `categories` is an array. Store money as `Decimal128` and dates as BSON dates.

`films` (one document per film, 1,000 documents):

```json
{
  "_id": 1,
  "title": "ACADEMY DINOSAUR",
  "release_year": 2012,
  "language": "English",
  "rating": "PG",
  "length": 86,
  "rental_duration": 6,
  "rental_rate": { "$numberDecimal": "0.99" },
  "categories": ["Games", "New", "Travel"],
  "actors": [{ "actor_id": 1, "name": "PENELOPE GUINESS" }, { "actor_id": 10, "name": "CHRISTIAN GABLE" }]
}
```

`customers` (one document per customer, 999 documents; `recent_rentals` holds the 10 most recent rentals, ordered by `rental_date` descending and then `rental_id` descending):

```json
{
  "_id": 1,
  "first_name": "MARY",
  "last_name": "SMITH",
  "email": "MARY.SMITH@sakilacustomer.org",
  "store_id": 1,
  "address": { "city": "Sasebo", "country": "Japan" },
  "rental_count": 66,
  "recent_rentals": [
    { "rental_id": 87420, "film_id": 307, "title": "FELLOWSHIP AUTUMN",
      "rental_date": { "$date": "2026-07-23T01:38:34.193Z" }, "return_date": null }
  ]
}
```

`rentals` (one document per rental, 51,805 documents; `amount` is the sum of the payments of that rental, 0 when there are none):

```json
{
  "_id": 87420,
  "customer_id": 1,
  "film_id": 307,
  "title": "FELLOWSHIP AUTUMN",
  "categories": ["Children", "Family", "Sci-Fi"],
  "store_id": 1,
  "rental_date": { "$date": "2026-07-23T01:38:34.193Z" },
  "return_date": null,
  "amount": { "$numberDecimal": "0" }
}
```

The examples are film 1, customer 1 and the most recent rental of customer 1 (some arrays are shortened).

**Tasks.**

1. `load.py` reads Pagila and writes the three collections. Running it twice must leave the same documents (use the Pagila IDs as `_id` and upserts or `replace_one`). In the README, justify why actors and categories are embedded in `films`, why only 10 rentals are embedded in `customers`, and why the full history is in `rentals`.
2. Write these 8 operations in `operations.js` (for `mongosh`) and record the result of each one:
   1. films rated `PG-13` and longer than 120 minutes. Expected: 118 documents.
   2. films in which actor 1 appears. Expected: 19 documents.
   3. films in the category `Horror` with a rental rate of 0.99. Expected: 43 documents.
   4. customers with at least one rental not returned among their `recent_rentals` (use `$elemMatch`). Expected: 56 documents.
   5. customer 1 with only `first_name`, `last_name` and the titles of `recent_rentals` (projection). Expected: 1 document with 10 titles.
   6. raise by 0.50 the rental rate of films rated `NC-17` shorter than 60 minutes (`updateMany` with `$inc`). Expected: 21 documents modified.
   7. add a rental to the front of customer 1's `recent_rentals` and keep only 10 (`$push` with `$each`, `$position` and `$slice`). Expected: `recent_rentals` still has 10 items and the first one is the new rental.
   8. an `updateOne` with `upsert: true` and `$setOnInsert` that creates the film `{_id: 1001, title: "TEST FILM"}`, run twice. Expected: the first run upserts 1 document; the second matches 1 and modifies 0.
3. Add `$jsonSchema` validation to `films` (`validationLevel: "strict"`, `validationAction: "error"`): `title` string, `rating` one of `G`, `PG`, `PG-13`, `R`, `NC-17`, `length` integer between 1 and 999, `rental_rate` decimal, `categories` array of strings, `actors` array of objects with `actor_id` integer and `name` string. Show that `load.py` still runs, and that a document with `rating: "XXX"` and one with `length: "long"` are rejected.
4. Run `find({"actors.actor_id": 1}).explain("executionStats")` before and after creating an index on `actors.actor_id`, and compare `stage`, `totalDocsExamined` and `nReturned`.

**Deliverables.**

- `load.py`, `pyproject.toml`, `operations.js`, `validation.js`, `index.js`.
- `README.md` with the commands to run each file, the justifications of task 1, the result of each operation, the rejected inserts with their error and the two `explain` summaries.

**Done when.** The three collections have 1,000, 999 and 51,805 documents, every operation returns the expected result on freshly loaded collections, both invalid documents are rejected, and the plan changes from `COLLSCAN` to `IXSCAN` with 19 documents examined.

## Challenge (opcional, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [ ] `load.py`: `films`, `customers`, `rentals` (1,000 / 999 / 51,805), idempotent, with justifications
- [ ] `operations.js`: 8 operations with expected results
- [ ] `validation.js`: `$jsonSchema` on `films`, two invalid documents rejected
- [ ] `index.js`: `explain` before and after (`COLLSCAN` -> `IXSCAN`, 19 examined)
