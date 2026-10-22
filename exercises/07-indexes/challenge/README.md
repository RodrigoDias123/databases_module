# Challenge 07: Indexes and optimisation

Obrigatório.

## Enunciado

Paginate `big_rental` for one customer sorted by date, 20 rows per page. Compare page 5,000 using `OFFSET` with the same page using keyset pagination (`WHERE (rented_at, id) < (:last_rented_at, :last_id)`). Then add `INCLUDE` columns to make the keyset query an index only scan, and explain what `VACUUM` has to do with the "Heap Fetches" line in the plan.
