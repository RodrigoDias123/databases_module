#!/usr/bin/env bash
# Custom-format dump of pagila plus a .counts file with the row count of every
# table, both taken from the same snapshot, then the retention policy:
#   - the latest backup of each of the last 7 days (today included);
#   - the latest backup of each of the last 4 ISO weeks (this week included).
# Everything else older than "now" is deleted.
# Usage:
#   ./backup.sh                          today, current time
#   ./backup.sh --now 2026-10-01         pretend today is 2026-10-01 (current time)
#   ./backup.sh --now 2026-10-01T0300    pretend it is 2026-10-01 03:00
# Environment: BACKUP_DIR (default: backups/ next to this script), DB (default: pagila).
# Needs GNU date and bash 4 (associative arrays).
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
backup_dir="$(mkdir -p "${BACKUP_DIR:-$script_dir/backups}" && cd "${BACKUP_DIR:-$script_dir/backups}" && pwd)"
db="${DB:-pagila}"

now_date="$(date +%F)"
now_time="$(date +%H%M)"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --now)
            arg="${2:?--now needs YYYY-MM-DD or YYYY-MM-DDTHHMM}"
            if [[ "$arg" =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2})(T([0-9]{4}))?$ ]]; then
                now_date="${BASH_REMATCH[1]}"
                [[ -n "${BASH_REMATCH[3]}" ]] && now_time="${BASH_REMATCH[3]}"
                date -d "$now_date" +%F > /dev/null   # rejects 2026-02-30
            else
                echo "Invalid --now: $arg (expected YYYY-MM-DD or YYYY-MM-DDTHHMM)" >&2
                exit 2
            fi
            shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

cd "$repo_root"
set -a; source .env; set +a

log() { echo "$(date '+%F %T') backup: $*"; }

name="${db}_${now_date}_${now_time}"
dump="$backup_dir/$name.dump"
counts="$backup_dir/$name.counts"

# --- 1. Dump and counts from one snapshot ---------------------------------
# A psql session opens a REPEATABLE READ transaction and exports its snapshot;
# pg_dump --snapshot reads exactly the same data, and the counts are taken in
# that same transaction, so the .counts file describes the dump even if the
# database is being written to meanwhile.
coproc PSQL { docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$db" \
                  -qtAX -v ON_ERROR_STOP=1 -F "$(printf '\t')"; }
# Copies of the coproc's pipes: the PSQL array is unset when psql exits.
exec {to_psql}>&"${PSQL[1]}" {from_psql}<&"${PSQL[0]}"
exec {PSQL[1]}>&- {PSQL[0]}<&-

printf 'BEGIN ISOLATION LEVEL REPEATABLE READ;\nSELECT pg_export_snapshot();\n' >&"$to_psql"
read -r snapshot <&"$from_psql"

trap 'rm -f "$dump.tmp" "$counts.tmp"' EXIT
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -Fc --snapshot="$snapshot" "$db" > "$dump.tmp"

{ cat "$script_dir/counts.sql"; printf '\\echo __END__\n'; } >&"$to_psql"
: > "$counts.tmp"
while IFS= read -r line <&"$from_psql"; do
    [[ "$line" == "__END__" ]] && break
    printf '%s\n' "$line" >> "$counts.tmp"
done
printf 'COMMIT;\n' >&"$to_psql"
exec {to_psql}>&-
wait "$PSQL_PID"
exec {from_psql}<&-

[[ -s "$counts.tmp" ]] || { log "no counts returned"; exit 1; }
mv "$dump.tmp" "$dump"
mv "$counts.tmp" "$counts"
trap - EXIT
log "wrote $name.dump ($(du -h "$dump" | cut -f1)) and $name.counts ($(wc -l < "$counts") tables)"

# --- 2. Retention -----------------------------------------------------------
declare -A keep_days keep_weeks
for i in 0 1 2 3 4 5 6; do keep_days["$(date -d "$now_date - $i days" +%F)"]=; done
for i in 0 1 2 3; do keep_weeks["$(date -d "$now_date - $((7 * i)) days" +%G-W%V)"]=; done

# File names sort in time order, so the last file seen for a day or a week is
# the latest one.
declare -A latest_of_day latest_of_week
mapfile -t files < <(find "$backup_dir" -maxdepth 1 -name "${db}_????-??-??_????.dump" -printf '%f\n' | sort)
for f in "${files[@]}"; do
    day="${f#"${db}_"}"; day="${day%%_*}"
    [[ "$day" > "$now_date" ]] && continue
    [[ -v keep_days[$day] ]] && latest_of_day[$day]="$f"
    week="$(date -d "$day" +%G-W%V)"
    [[ -v keep_weeks[$week] ]] && latest_of_week[$week]="$f"
done

declare -A keep
for f in "${latest_of_day[@]}" "${latest_of_week[@]}"; do keep[$f]=; done

for f in "${files[@]}"; do
    day="${f#"${db}_"}"; day="${day%%_*}"
    if [[ "$day" > "$now_date" ]]; then
        log "kept $f: dated after $now_date"
    elif [[ ! -v keep[$f] ]]; then
        rm -f "$backup_dir/$f" "$backup_dir/${f%.dump}.counts"
        log "deleted ${f%.dump}"
    fi
done
log "retention for $now_date: ${#latest_of_day[@]} daily, ${#latest_of_week[@]} weekly, ${#keep[@]} backups kept"
