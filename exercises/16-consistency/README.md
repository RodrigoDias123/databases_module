# Exercício 16: Redis II, source of truth, rebuild and persistence

## Enunciado

Folder: `exercises/16-consistency/`

1. A Redis set per customer with the categories they have rented from (`customer:{id}:categories`), filled from PostgreSQL. Then `FLUSHALL` and rebuild every set with a script that uses one query and one pipeline.
2. A verification script that compares every set with PostgreSQL (size and members) and exits with an error if any differs.
3. For each structure from exercises 15 and 16, say whether it is source of truth, derived or ephemeral, choose its persistence and eviction policy, and justify each choice.

Marked 2 when rebuild and verification work and the justifications are correct.

Group project: Redis rebuild, source-of-truth table in the README, persistence. Milestone M4 closes at the end of this session.

## Challenge (obrigatório, em `challenge/`)

Implement the transactional outbox pattern: in the same PostgreSQL transaction as each new rental, insert a row into an `outbox` table. A separate worker reads unprocessed outbox rows (`FOR UPDATE SKIP LOCKED`), adds the film's category to `customer:{id}:categories` and marks the row processed. Kill the worker mid-batch and kill Redis mid-batch, restart both, and show with your verification script that Redis ends up correct without a full rebuild.

## Checklist

- [ ] `customer:{id}:categories` sets filled from PostgreSQL
- [ ] FLUSHALL and rebuild with one query and one pipeline
- [ ] Verification script comparing every set with PostgreSQL (exits with error on mismatch)
- [ ] For each structure from ex. 15 and 16: source of truth / derived / ephemeral, persistence and eviction policy, justified
