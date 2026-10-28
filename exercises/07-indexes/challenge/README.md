# Challenge 07: Indexes and optimisation

Obrigatório.

## Enunciado

Folder: `exercises/07-indexes/challenge/`

**Goal.** Compare `OFFSET` pagination with keyset pagination, and connect index only scans to `VACUUM`.

**Starting point.** The `big_rental` table of the exercise above, created with its `setup.sql` in a database of its own (`./scripts/create-db.sh ch07 --reset`). Pages are 20 rows of the whole table ordered by `rented_at DESC, id DESC`. Page 5,000 starts after 99,980 rows.

**Tasks.**

1. Create an index that matches the sort order.
2. Read page 5,000 with `ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20` and record its plan and time with `EXPLAIN (ANALYZE, BUFFERS)`.
3. Read the same page with keyset pagination. Store the last row of page 4,999 in psql variables, then use them:

   ```sql
   SELECT rented_at AS last_rented_at, id AS last_id
   FROM big_rental ORDER BY rented_at DESC, id DESC OFFSET 99979 LIMIT 1 \gset

   SELECT id, rented_at, customer_id FROM big_rental
   WHERE (rented_at, id) < (:'last_rented_at', :last_id)
   ORDER BY rented_at DESC, id DESC LIMIT 20;
   ```

   Show that both queries return the same 20 rows, and compare the plans and times.
4. Recreate the index with `INCLUDE (customer_id)` so that the keyset query becomes an `Index Only Scan`.
5. Run `UPDATE big_rental SET customer_id = customer_id WHERE id % 50 = 0;`, run the keyset query again and read the `Heap Fetches` line. Then run `VACUUM big_rental;` and run it once more.

**Deliverables.**

- `pagination.sql` with every statement in order.
- `README.md` with the plans and times of tasks 2, 3 and 5, and an explanation of why `OFFSET` gets slower as the page number grows, and of what `VACUUM` changes in the visibility map that makes `Heap Fetches` drop.

**Done when.** The two methods return the same rows, the keyset query does not depend on the page number, the plan of task 4 is an `Index Only Scan`, and `Heap Fetches` is above 0 after the update and 0 after `VACUUM`.
