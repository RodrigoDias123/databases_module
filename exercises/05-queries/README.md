# Exercício 05: Queries I, joins, aggregation, subqueries and CTEs

## Enunciado

Folder: `exercises/05-queries/exercise/`

**Goal.** Answer business questions with joins, aggregation, subqueries and CTEs.

**Starting point.** A fresh copy of Pagila (`./scripts/create-db.sh ex05 --pagila --reset`). In this version of Pagila a film can belong to more than one category; when a question is per category, a film counts in each of its categories.

**Tasks.** Write one query per question. Window functions are not allowed in this exercise (they are the topic of session 06).

1. The number of films per category, including categories with no films, most films first, then by category name. Expected: 16 rows; the first two are `Drama` and `Music`, with 152 films each.
2. Revenue per category per month in 2025, by `payment_date`. Expected: 192 rows; `Action` in January 2025 has 314.94.
3. Films that have never been rented, including films with no copy in any store. Expected: 42 rows.
4. Customers who have rented films of all 5 ratings. Expected: 908 rows.
5. Pairs of actors who appeared together in more than 3 films, each pair listed once, with the number of films (self join). Expected: 143 rows.
6. Countries with more than 20 customers, with the number of customers and the total they paid, most customers first. Expected: 7 rows; the first is `Mexico` with 430 customers.
7. Customers who paid more in total than the average customer of their own country. A customer with no payments counts as 0. Expected: 449 rows.
8. The longest films of each rating, including ties, using a subquery. Expected: 14 rows.
9. Customers with no rental on or after `2026-04-01`. Expected: 49 rows.
10. For each category, the average number of days a film stays out (`return_date - rental_date`, returned rentals only), rounded to 2 decimals, highest first. Expected: 16 rows; the first is `Sci-Fi` with 5.30.

**Deliverables.**

- `queries.sql` with the 10 queries, each preceded by a comment with its number and the question.
- `README.md` with the row count and the first 5 rows of each result.

**Done when.** Every query runs on a fresh copy and returns the expected number of rows and values.

## Challenge (obrigatório, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [ ] `queries.sql` with the 10 queries, each preceded by its number and question
- [ ] No window functions
- [ ] Runs on a fresh copy (`ex05`) with `ON_ERROR_STOP=1`
- [ ] Every query returns the expected number of rows and values
- [ ] `README.md` with the row count and the first 5 rows of each result

## Resposta

Resposta em [exercise/README.md](exercise/README.md).
