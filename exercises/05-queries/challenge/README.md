# Challenge 05: Queries I, joins, aggregation, subqueries and CTEs

Obrigatório.

## Enunciado

Using a recursive CTE (`WITH RECURSIVE`), compute the "degrees of separation" between actors: two actors are at distance 1 if they appeared in the same film. Given one actor, list every actor reachable within 3 degrees and the shortest distance to each. Make sure the query terminates and does not revisit actors.
