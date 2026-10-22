# Exercício 10: Backup and restore

## Enunciado

Folder: `exercises/10-backup/runbook.md`

At the start, back up your Pagila. Halfway through, the trainer runs a script that deletes data from 3 tables. Recover the data and document: the commands used, the measured restore time, what was lost between the backup and the disaster (real RPO), and what you would change in your strategy.

## Challenge (obrigatório, em `challenge/`)

Write `backup.sh` that takes a custom-format dump with a timestamped name and applies a retention policy of 7 daily and 4 weekly backups. Write `verify.sh` that restores the latest dump into a throwaway container, compares row counts of every table against the live database, and exits with a non-zero code on any mismatch. Schedule both with cron and show a log of two runs.
