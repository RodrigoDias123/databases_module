# Exercício 06: Queries II, window functions and views

## Enunciado

Folder: `exercises/06-window/exercise/`

**Goal.** Rank, accumulate and compare rows with window functions, and keep a report in a materialised view.

**Starting point.** A fresh copy of Pagila (`./scripts/create-db.sh ex06 --pagila --reset`).

**Tasks.**

1. The 3 most rented films of each category, by number of rentals. Films tied on the same number share a position, and every film in positions 1 to 3 is listed. Expected: 56 rows.
2. Revenue per day in July 2026, with the running total for the month. Columns: `day`, `revenue`, `running_total`. Expected: 28 rows; the last running total is 2409.88.
3. Revenue per month for the whole data set, with the change from the previous month in value and in percentage (1 decimal). Expected: 55 rows; July 2026 has 2409.88, the previous month 2105.73, a change of 304.15 and 14.4%.
4. Each customer's position in the ranking of their store by total paid. Customers with no payments count as 0, and tied customers share a position. Expected: 999 rows; customer 468 is first in store 1 (344.06) and customer 526 is first in store 2 (358.12).
5. The top 5 customers of each store by total paid. Expected: 10 rows.

**Deliverables.**

- `queries.sql` with the 6 tasks, each preceded by a comment with its number.
- `README.md` with the row count and the first 5 rows of each result, and the output of the steps of task 6.

**Done when.** Every query runs on a fresh copy and returns the expected rows and values, and the materialised view changes only after the refresh.

## Challenge (obrigatório, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).
