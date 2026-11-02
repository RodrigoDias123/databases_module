# Runbook: restore deleted rows of `payment`, `film_actor` and `film_category` from a `pg_dump`

## When to use it

Use it when rows of `payment`, `film_actor` or `film_category` were deleted by mistake (a bad `DELETE`, a script run against the wrong database) and the database itself is still up. It puts back the data of those tables as it was in the most recent custom-format backup, without dropping or recreating the database, so every other table, role and connection is left alone.

Do not use it when:

- the database or the server is gone: restore the whole dump into a new database instead (`pg_restore -d <new db>`) and switch the application to it;
- rows were added to these tables after the backup and were **not** deleted by the incident: `TRUNCATE` would delete them too. Restore into a separate database and copy only the missing rows (see [Alternative: copy only the missing rows](#alternative-copy-only-the-missing-rows));
- other tables were damaged as well: this runbook only touches the three tables above.

The incident this runbook was written and tested for (`disaster.sql`):

```sql
DELETE FROM payment WHERE payment_date >= '2026-01-01';   -- partitions payment_p2026_01 to payment_p2026_07
DELETE FROM film_actor WHERE actor_id <= 50;
DELETE FROM film_category WHERE category_id = 1;
```

## Prerequisites

- The Docker Compose stack of this repository is running (`docker compose ps` shows `postgres` as healthy) and `.env` exists at the root of the repository.
- A custom-format backup (`pg_dump -Fc`) of the database taken **before** the incident, in `backups/` at the root of the repository. In this run: `backups/ex10_20261030.dump`, taken at 2026-10-30 20:59:52 UTC.
- `psql` can reach the server (the dev container sets `PGHOST` and `PGUSER`; otherwise add `-h localhost -U postgres`).
- Write access to the target database as `postgres` (the restore runs `TRUNCATE` and `COPY`).
- The application that writes to these tables is stopped or put in maintenance mode, so nothing is written while the tables are reloaded.
- No other table has a foreign key to `payment`, `film_actor` or `film_category`, so they can be emptied with `TRUNCATE`. Check it once with:

  ```sql
  SELECT conrelid::regclass, conname
  FROM pg_constraint
  WHERE contype = 'f'
    AND confrelid IN ('payment'::regclass, 'film_actor'::regclass, 'film_category'::regclass);
  -- expected: 0 rows
  ```

All commands below run from the **root of the repository**. The files they use are in `exercises/10-backup/exercise/`:

| File | What it does |
|------|--------------|
| `counts.sql` | Row counts of the three tables. |
| `activity.sql` | Normal work after the backup: 5 payments of 1.99 on 2026-07-30. |
| `disaster.sql` | The incident. |
| `restore.sh` | `TRUNCATE` of the 7 partitions and the two tables, then `pg_restore --data-only` of the same tables, in one transaction. |
| `rpo.sql` | Shows the payments written after the backup that are lost. |
| `verify.sql` | Row count and checksum of each table, to compare with a full restore of the same dump. |

## Commands, in order

### 0. Set up the scenario (exercise only)

```bash
docker compose up -d
./scripts/create-db.sh ex10 --pagila --reset
mkdir -p backups
```

### 1. Row counts before the backup

```bash
psql -d ex10 -f exercises/10-backup/exercise/counts.sql
```

### 2. Back up in custom format and note the time

```bash
date -u +"%Y-%m-%d %H:%M:%S UTC"
docker compose exec -T postgres pg_dump -U postgres -Fc ex10 > backups/ex10_20261030.dump
ls -l backups/ex10_20261030.dump          # about 4.6 MB
```

`-T` is needed: without it Docker allocates a terminal and corrupts the binary output.

### 3. Activity after the backup, then the incident

```bash
psql -d ex10 -v ON_ERROR_STOP=1 -f exercises/10-backup/exercise/activity.sql   # INSERT 0 5
psql -d ex10 -v ON_ERROR_STOP=1 -f exercises/10-backup/exercise/disaster.sql   # DELETE 5286 / 1327 / 149
psql -d ex10 -f exercises/10-backup/exercise/counts.sql
```

### 4. Restore (timed)

In a real incident, first save the damaged state, so nothing written after the backup is destroyed for good:

```bash
docker compose exec -T postgres pg_dump -U postgres -Fc ex10 > backups/ex10_before_restore.dump
```

Optional: check what the dump holds for these tables before restoring:

```bash
docker compose exec -T postgres pg_restore -l < backups/ex10_20261030.dump \
  | grep -E 'TABLE DATA public (payment_p2026_0[1-7]|film_actor|film_category) '
```

Then restore:

```bash
time ./exercises/10-backup/exercise/restore.sh ex10 backups/ex10_20261030.dump
```

What `restore.sh` sends to `psql`, in one transaction (`--single-transaction`, `ON_ERROR_STOP=1`: on any error nothing is changed):

```sql
TRUNCATE payment_p2026_01, payment_p2026_02, payment_p2026_03, payment_p2026_04,
         payment_p2026_05, payment_p2026_06, payment_p2026_07, film_actor, film_category;
-- followed by the output of:
--   pg_restore --data-only -t payment_p2026_01 ... -t payment_p2026_07 -t film_actor -t film_category -f -
-- which is one COPY ... FROM stdin per table, with the rows from the dump
```

Why it is done this way:

- `payment` is partitioned. Its rows live in the partitions, so `-t payment` selects a table with no data. Each partition that lost rows (`payment_p2026_01` to `payment_p2026_07`) is named with its own `-t`. The partitions of 2022 to 2025 were not touched and are left alone.
- `pg_restore --clean -t payment` would try `DROP TABLE payment`, which fails because views (`sales_by_store`, `sales_by_film_category`) and a materialised view depend on it. `--data-only` keeps the table definitions and only reloads rows.
- `film_actor` and `film_category` still held part of their rows. Loading the dump on top of them would fail on the primary key, so they are emptied first and reloaded whole.
- The `last_updated` triggers of `film_actor` and `film_category` only fire on `UPDATE`, so `COPY` keeps the original `last_update` values.
- The `payment_payment_id_seq` sequence is **not** restored, on purpose: it keeps its current value, so new payments do not reuse ids that were already handed out, and it still shows how many payments were lost (step 6).

### 5. Row counts after the restore

```bash
psql -d ex10 -f exercises/10-backup/exercise/counts.sql
```

### 6. What was lost (RPO)

```bash
psql -d ex10 -f exercises/10-backup/exercise/rpo.sql
```

```sql
SELECT max(payment_id)                                   AS last_id_in_backup,
       (SELECT last_value FROM payment_payment_id_seq)   AS last_id_issued,
       (SELECT last_value FROM payment_payment_id_seq) - max(payment_id) AS payments_lost
FROM payment;

SELECT r.rental_id, r.customer_id, r.staff_id,
       p.payment_id IS NOT NULL AS payment_2026_07_30_present
FROM (SELECT * FROM rental ORDER BY rental_id DESC LIMIT 5) AS r
LEFT JOIN payment p
       ON p.rental_id = r.rental_id
      AND p.payment_date = timestamptz '2026-07-30 12:00+00'
ORDER BY r.rental_id DESC;
```

### 7. Verify

See [How to verify the restore](#how-to-verify-the-restore).

### 8. Clean up

```bash
psql -d postgres -c 'DROP DATABASE IF EXISTS ex10_check;'
```

Keep the dumps in `backups/` (ignored by Git: they hold all the data) until the incident is closed.

## Results of this run

PostgreSQL 18.6, 2026-10-30. Backup at 20:59:52 UTC, incident at 20:59:58 UTC.

### Row counts

| Table | Task 1: before the backup | Task 3: after the incident | Task 5: after the restore |
|-------|--------------------------:|---------------------------:|--------------------------:|
| `payment` | 51 061 | 45 780 (−5 286) | 51 061 |
| `film_actor` | 5 462 | 4 135 (−1 327) | 5 462 |
| `film_category` | 2 367 | 2 218 (−149) | 2 367 |

`activity.sql` brought `payment` to 51 066 just before the incident. The incident deleted 5 286 payments: the 5 281 of the backup plus the 5 new ones. After the restore `payment` is back to 51 061, the count of task 1, not 51 066: the 5 new payments are lost.

### Restore time (real RTO)

| What | Time |
|------|-----:|
| `restore.sh` (`TRUNCATE` + reload of 9 tables, 6 757 rows) | **0.144 s** (`real`, same in two runs) |
| Full restore of the 4.6 MB dump into a new database (`ex10_check`) | 0.417 s |
| Steps 1 to 7 run one after the other (the second run) | a few seconds |

The technical restore is a fraction of a second on Pagila. The real RTO is set by the people: noticing the incident, finding the right dump, stopping the application, and verifying. With a production-sized table the reload grows roughly with the number of rows; time it on a copy before relying on it.

### Data lost between the backup and the incident (real RPO)

In time: everything written between the backup (20:59:52) and the incident (20:59:58), **6 seconds** in this run. In a real system it is the time since the last backup, up to a full day with daily dumps.

In data: **the 5 payments of `activity.sql`** (5 × 1.99 = 9.95), with ids 102 095 to 102 099. Output of `rpo.sql` after the restore:

```text
 last_id_in_backup | last_id_issued | payments_lost
-------------------+----------------+---------------
            102094 |         102099 |             5

 rental_id | customer_id | staff_id | payment_2026_07_30_present
-----------+-------------+----------+----------------------------
     87559 |           3 |        1 | f
     87558 |         676 |        2 | f
     87557 |         484 |        1 | f
     87556 |         715 |        2 | f
     87555 |         250 |        2 | f
```

The restored table ends at id 102 094 (the last payment in the backup), but the sequence has already handed out ids up to 102 099: 5 payments were written after the backup and are in neither the database nor the dump. The second query names them: the 5 most recent rentals have no payment on 2026-07-30. They must be entered again from another source (the till, the payment provider's records) or the customers charged again.

`film_actor` and `film_category` lost nothing: no rows were written to them between the backup and the incident.

## How to verify the restore

1. **Row counts** (step 5) must match the counts taken before the backup, or, in a real incident, `pg_restore -l` plus a full restore of the same dump.
2. **Content, not just counts.** Restore the same dump in full into a separate database and compare a checksum of every row of the three tables:

   ```bash
   ./scripts/create-db.sh ex10_check --reset
   docker compose exec -T postgres pg_restore -U postgres -d ex10_check --no-owner < backups/ex10_20261030.dump
   psql -d ex10 -tA -f exercises/10-backup/exercise/verify.sql \
     | diff - <(psql -d ex10_check -tA -f exercises/10-backup/exercise/verify.sql) \
     && echo "verify: identical"
   ```

   Expected output of `verify.sql` in both databases (this run):

   ```text
   payment|51061|2384c7d5e33d74e757ea181b74e20ebb
   film_actor|5462|80aab112657665327b28e1092655647f
   film_category|2367|31e93fd5dabd78d6bf24492d42fbf884
   verify: identical
   ```

3. **Each damaged slice is back:**

   ```sql
   SELECT count(*) FROM payment WHERE payment_date >= '2026-01-01';   -- 5281
   SELECT count(*) FROM film_actor WHERE actor_id <= 50;              -- 1327
   SELECT count(*) FROM film_category WHERE category_id = 1;          -- 149
   ```

4. **The views that read these tables work:** `SELECT * FROM sales_by_store;` and `SELECT * FROM sales_by_film_category LIMIT 5;` return rows.
5. **New payments get new ids:** the next `nextval('payment_payment_id_seq')` is above 102 099, so no lost id is reused.
6. Run `rpo.sql` and record the lost payments in the incident report, then tell the application owner which payments must be entered again.

## Alternative: copy only the missing rows

When the tables have rows written after the backup that survived the incident, do not `TRUNCATE`. Restore the dump into `ex10_check` (as in verification, step 2) and insert only the rows that are missing, for example with `postgres_fdw` or by exporting from `ex10_check` with `\copy` into a staging table:

```sql
-- in ex10, after loading ex10_check's film_actor into a staging table restore_film_actor
INSERT INTO film_actor
SELECT * FROM restore_film_actor
EXCEPT
SELECT * FROM film_actor;
```

This keeps every row that is still there and only adds back what was deleted.

## What I would change in the backup strategy to lose less

- **Continuous WAL archiving with point-in-time recovery (PITR).** A base backup plus archived WAL (`archive_mode = on` with `pgBackRest` or `pg_basebackup` + `archive_command`) lets the database be recovered to the second just before the `DELETE` (`recovery_target_time = '2026-10-30 20:59:57'`). The 5 payments of `activity.sql` would not be lost: RPO goes from "time since the last dump" to seconds.
- **A delayed standby.** A streaming replica with `recovery_min_apply_delay = '1h'` keeps a copy one hour behind. After a bad `DELETE`, pause replay on it and copy the rows back: RTO of minutes, RPO close to zero for logical mistakes, which a normal replica copies instantly.
- **More frequent dumps** where PITR is not possible: hourly instead of daily, named with date and time, so the RPO is at most one hour.
- **Backups off the server**, in another location, with retention (for example 7 daily, 4 weekly, 12 monthly). A dump on the same disk is lost with the server. Back up the roles too (`pg_dumpall --roles-only`), and keep both out of Git.
- **Tested restores**, scheduled: restore the latest dump into a clean container, run `verify.sql`, and record the time. A backup that was never restored is not a backup, and the timed run is what gives the real RTO.
- **Prevention**: the application role should not be able to run a `DELETE` without a `WHERE` on these tables, maintenance scripts run inside `BEGIN` with a check of the row count before `COMMIT`, and a dump is taken right before any risky manual change.
