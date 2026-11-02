#!/usr/bin/env bash
# Restores the data of payment (partitions 2026_01 to 2026_07), film_actor and
# film_category into an existing database from a pg_dump custom-format file.
# The database is not dropped: each table is emptied with TRUNCATE and reloaded
# with pg_restore --data-only, inside one transaction.
# Usage, from the root of the repository:
#   ./exercises/10-backup/exercise/restore.sh ex10 backups/ex10_20261030.dump
set -euo pipefail

cd "$(dirname "$0")/../../.."
set -a; source .env; set +a

db="${1:?Usage: restore.sh <database> <dump file>}"
dump="${2:?Usage: restore.sh <database> <dump file>}"

partitions=(payment_p2026_01 payment_p2026_02 payment_p2026_03 payment_p2026_04
            payment_p2026_05 payment_p2026_06 payment_p2026_07)
tables=("${partitions[@]}" film_actor film_category)

# TRUNCATE and the reload must run in the same session for --single-transaction
# to cover both, so the TRUNCATE goes in front of the SQL that pg_restore writes.
table_args=()
for t in "${tables[@]}"; do table_args+=(-t "$t"); done

{
    echo "TRUNCATE $(IFS=,; echo "${tables[*]}");"
    docker compose exec -T postgres pg_restore --data-only "${table_args[@]}" -f - < "$dump"
} | docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$db" \
        -v ON_ERROR_STOP=1 --single-transaction -q -o /dev/null
