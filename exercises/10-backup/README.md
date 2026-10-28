# Exercício 10: Backup and restore

## Enunciado

Folder: `exercises/10-backup/exercise/`

**Goal.** Recover from a data loss with a backup, measure what was lost, and write a runbook someone else can follow.

**Starting point.** A fresh copy of Pagila (`./scripts/create-db.sh ex10 --pagila --reset`) and these two scripts, saved in your exercise folder. Do not read ahead to fix the damage before it happens: follow the steps in order.

`activity.sql` (normal work that happens after the backup):

```sql
INSERT INTO payment (customer_id, staff_id, rental_id, amount, payment_date)
SELECT customer_id, staff_id, rental_id, 1.99, timestamptz '2026-07-30 12:00+00'
FROM rental ORDER BY rental_id DESC LIMIT 5;
```

`disaster.sql` (the incident):

```sql
BEGIN;
DELETE FROM payment WHERE payment_date >= '2026-01-01';
DELETE FROM film_actor WHERE actor_id <= 50;
DELETE FROM film_category WHERE category_id = 1;
COMMIT;
```

**Tasks.**

1. Record the row counts of `payment`, `film_actor` and `film_category`.
2. Back up `ex10` in custom format into `backups/` (as in the tutorial) and note the time.
3. Run `activity.sql`, then `disaster.sql`, on `ex10`. Record the row counts again.
4. Restore the deleted data into `ex10` from your backup, without dropping or recreating the database. Time the restore. Remember that `payment` is partitioned: the rows deleted are in the partitions `payment_p2026_01` to `payment_p2026_07`. `film_actor` and `film_category` still hold part of their rows, so restoring only the missing ones needs a plan (for example `TRUNCATE` and reload, or restore into another database and copy the missing rows).
5. Record the row counts after the restore and compare them with tasks 1 and 3.
6. Write the runbook for this incident.

**Deliverables.** `runbook.md` with:

- when to use it and the prerequisites;
- every command you ran, in order, so that someone else can repeat them;
- the row counts of tasks 1, 3 and 5;
- the measured restore time (real RTO);
- the data lost between the backup and the incident (real RPO), with the query that shows it;
- how to verify the restore;
- what you would change in your backup strategy to lose less.

**Done when.** After the restore, the three tables have the same row counts as in task 1, the 5 payments of `activity.sql` are identified as lost, and the runbook can be followed without your help.

## Challenge (opcional, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).
