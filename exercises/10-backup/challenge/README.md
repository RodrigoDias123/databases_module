# Challenge 10: Backup and restore

Opcional.

## Enunciado

Folder: `exercises/10-backup/challenge/`

**Goal.** Automate backups with retention and check every backup by restoring it.

**Starting point.** The `pagila` database and the tutorial of this session.

**Tasks.**

1. `backup.sh` takes a custom-format dump of `pagila` named `pagila_YYYY-MM-DD_HHMM.dump` and, next to it, a file `pagila_YYYY-MM-DD_HHMM.counts` with the row count of every table at the time of the dump. It then applies a retention policy: keep the latest backup of each of the last 7 days, and the latest backup of each of the last 4 weeks; delete the rest. Accept an optional `--now YYYY-MM-DD` argument that replaces today's date, so that the retention can be tested without waiting weeks.
2. `verify.sh` restores the latest dump into a throwaway container (`docker run --rm ... postgres:18`), counts the rows of every table, compares them with the `.counts` file of that dump, prints every difference and exits with a non-zero code if there is any.
3. Test the retention: create backups for 40 simulated days with `--now` and show which files remain.
4. Schedule both scripts (cron on Linux and macOS, Task Scheduler or a loop in WSL on Windows) and show the log of two scheduled runs.

**Deliverables.**

- `backup.sh`, `verify.sh`.
- `README.md` with the schedule configuration, the list of files left by task 3, the log of task 4, and the output of `verify.sh` for a good dump and for a dump you changed on purpose.

**Done when.** After task 3 exactly the expected files remain (at most 7 daily and 4 weekly), `verify.sh` exits with 0 for a good dump and with a non-zero code for a changed one.
