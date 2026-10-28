# Challenge 06: Queries II, window functions and views

Obrigatório.

## Enunciado

Folder: `exercises/06-window/challenge/`

**Goal.** Solve a "gaps and islands" problem with window functions.

**Starting point.** A fresh copy of Pagila (`./scripts/create-db.sh ch06 --pagila --reset`). An island is a run of consecutive calendar months in which a customer rented at least one film. In Pagila, March and April 2022 have no rentals at all.

**Tasks.**

1. For each customer, find their longest island: `customer_id`, `first_month`, `last_month`, `months`. When a customer has two islands of the same length, keep the earliest.
2. Return the 10 customers with the longest islands, longest first, ties broken by `customer_id`.
3. Use window functions and set operations only: no procedural code, no recursive CTE.

**Deliverables.**

- `islands.sql` with the query.
- `README.md` with the 10 rows of the result and an explanation of the technique you used to group consecutive months.

**Done when.** The first row is customer 70 with 19 months, from 2023-06 to 2024-12, and the tenth row is customer 556 with 16 months.
