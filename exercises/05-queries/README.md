# Exercício 05: Queries I, joins, aggregation, subqueries and CTEs

## Enunciado

Folder: `exercises/05-queries/queries.sql`

10 business questions on Pagila. Examples: revenue per category per month; top 5 customers per store; films never rented; pairs of actors who appeared in more than 3 films together (self join); customers who spend more than the average of their city.

Marked 2 for 9 or 10 correct, 1 for 5 to 8.

Group project: finish the seed with the scenario's volume. Milestone M1 closes at the end of this session.

## Challenge (opcional, em `challenge/`)

Using a recursive CTE (`WITH RECURSIVE`), compute the "degrees of separation" between actors: two actors are at distance 1 if they appeared in the same film. Given one actor, list every actor reachable within 3 degrees and the shortest distance to each. Make sure the query terminates and does not revisit actors.
