#!/usr/bin/env bash
# Restores a dump into a throwaway postgres:18 container, counts the rows of
# every table and compares them with the .counts file written next to the dump
# by backup.sh. Prints every difference and exits with 1 if there is any, or
# if the restore itself fails.
# Usage:
#   ./verify.sh                      the latest pagila_*.dump in BACKUP_DIR
#   ./verify.sh path/to/x.dump       that dump (its x.counts must be next to it)
# Environment: BACKUP_DIR (default: backups/ next to this script), DB (default: pagila).
set -euo pipefail
export LC_ALL=C   # the same sort order for sort and join

script_dir="$(cd "$(dirname "$0")" && pwd)"
backup_dir="${BACKUP_DIR:-$script_dir/backups}"
db="${DB:-pagila}"

log() { echo "$(date '+%F %T') verify: $*"; }

if [[ $# -ge 1 ]]; then
    dump="$1"
else
    dump="$(find "$backup_dir" -maxdepth 1 -name "${db}_????-??-??_????.dump" | sort | tail -n 1)"
    [[ -n "$dump" ]] || { log "no ${db}_*.dump in $backup_dir"; exit 1; }
fi
counts="${dump%.dump}.counts"
[[ -f "$dump" ]] || { log "missing $dump"; exit 1; }
[[ -f "$counts" ]] || { log "missing $counts"; exit 1; }
log "checking $(basename "$dump")"

container="verify-${db}-$$"
docker run --rm -d --name "$container" -e POSTGRES_PASSWORD=verify postgres:18 > /dev/null
trap 'docker rm -f "$container" > /dev/null 2>&1 || true' EXIT

# The image runs initdb and restarts the server once; wait for the final one.
for _ in $(seq 60); do
    docker exec "$container" pg_isready -U postgres -h 127.0.0.1 -q 2>/dev/null \
        && docker exec "$container" psql -U postgres -h 127.0.0.1 -qtAc 'SELECT 1' > /dev/null 2>&1 \
        && break
    sleep 1
done

docker exec "$container" createdb -U postgres -h 127.0.0.1 "$db"
start=$(date +%s.%N)
if ! docker exec -i "$container" pg_restore -U postgres -h 127.0.0.1 -d "$db" \
        --no-owner --no-privileges --exit-on-error < "$dump"; then
    log "FAILED: pg_restore could not restore $(basename "$dump")"
    exit 1
fi
log "restored in $(awk -v s="$start" -v e="$(date +%s.%N)" 'BEGIN { printf "%.1f", e - s }') s"

restored="$(docker exec -i "$container" psql -U postgres -h 127.0.0.1 -d "$db" \
                -qtAX -v ON_ERROR_STOP=1 -F "$(printf '\t')" < "$script_dir/counts.sql")"

# Full outer join of the two lists on the table name.
differences="$(join -t $'\t' -a 1 -a 2 -e MISSING -o 0,1.2,2.2 \
                   <(sort "$counts") <(sort <<< "$restored") \
               | awk -F '\t' '$2 != $3 { printf "  %-28s expected %-8s restored %s\n", $1, $2, $3 }')"

tables=$(wc -l < "$counts")
if [[ -n "$differences" ]]; then
    log "FAILED: $(wc -l <<< "$differences") of $tables tables differ"
    echo "$differences"
    exit 1
fi
log "OK: all $tables tables have the expected row counts"
