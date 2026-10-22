# Exercício 06: Queries II, window functions and views

## Enunciado

Folder: `exercises/06-window/queries.sql`

Top 3 films per category (ties handled); cumulative revenue per day; change compared with the previous month; each customer's position in their store's ranking; a materialised view of monthly revenue with refresh.

## Challenge (obrigatório, em `challenge/`)

"Gaps and islands": for each customer, find the longest run of consecutive months in which they rented at least one film, with its start and end month. Solve it with window functions only (no procedural code). Then return the 10 customers with the longest runs.
