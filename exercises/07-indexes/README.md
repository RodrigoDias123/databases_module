# Exercício 07: Indexes and optimisation

## Enunciado

Folder: `exercises/07-indexes/README.md`

The script in the exercise folder creates a 2-million-row rental table. For each of the 5 queries: plan before, index created, plan after, times, and one sentence explaining the difference. Not every query can be fixed with an index; when one cannot, prove it with the plans and explain why.

Marked 2 when all 5 have evidence and any case an index cannot fix is correctly identified.

Group project: three slow queries from your scenario, the indexes you created, and before/after measurements in `docs/optimisation.md`.

## Challenge (opcional, em `challenge/`)

Paginate `big_rental` for one customer sorted by date, 20 rows per page. Compare page 5,000 using `OFFSET` with the same page using keyset pagination (`WHERE (rented_at, id) < (:last_rented_at, :last_id)`). Then add `INCLUDE` columns to make the keyset query an index only scan, and explain what `VACUUM` has to do with the "Heap Fetches" line in the plan.

## Checklist

- [ ] Query 1: plan before, index created, plan after, times, one-sentence explanation
- [ ] Query 2: plan before, index created, plan after, times, one-sentence explanation
- [ ] Query 3: plan before, index created, plan after, times, one-sentence explanation
- [ ] Query 4: plan before, index created, plan after, times, one-sentence explanation
- [ ] Query 5: plan before, index created, plan after, times, one-sentence explanation
- [ ] Identify (and prove with plans) any query an index cannot fix
