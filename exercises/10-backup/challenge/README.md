# Challenge 10: Backup and restore

Obrigatório.

## Enunciado

Write `backup.sh` that takes a custom-format dump with a timestamped name and applies a retention policy of 7 daily and 4 weekly backups. Write `verify.sh` that restores the latest dump into a throwaway container, compares row counts of every table against the live database, and exits with a non-zero code on any mismatch. Schedule both with cron and show a log of two runs.
