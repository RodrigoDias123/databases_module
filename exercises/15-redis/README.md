# Exercício 15: Redis I, data structures and patterns

## Enunciado

Folder: `exercises/15-redis/`

Using Pagila data:

1. "Recently viewed films" per customer: a sorted set with timestamps as scores, trimmed to the 20 most recent, expiring after 30 days without activity.
2. Cache-aside for a film's details with a TTL, invalidated when the film is updated.
3. A lock so that only one process at a time refreshes the monthly revenue materialised view from exercise 06, with safe release. Start two processes together and prove that only one runs the refresh.
4. A rate limit of 10 requests per minute per customer.

Marked 2 when all four patterns work.

Group project: your scenario's Redis structures: key names, TTLs and operations.

## Challenge (obrigatório, em `challenge/`)

The fixed-window rate limit above lets a client send 20 requests in two seconds (10 at the end of one minute, 10 at the start of the next). Implement a sliding-window rate limit with a sorted set (timestamps as scores), as a Lua script so that the check and the insert are atomic. Write a test that shows the burst passing the fixed window and being blocked by the sliding one.

## Checklist

- [ ] Recently viewed films per customer: sorted set, 20 most recent, expires after 30 days without activity
- [ ] Cache-aside for film details with TTL, invalidated on update
- [ ] Lock for refreshing the monthly revenue materialised view (ex. 06), safe release, proof with two processes
- [ ] Rate limit of 10 requests per minute per customer
