#!/usr/bin/env bash
# Challenge 16, task 3: rent.py 5000 while the worker runs; kill -9 the worker between its
# Redis write and its COMMIT, start it again; then kill Redis mid-batch and start it again
# with AOF (same -f files) and CONFIG SET appendfsync always before the worker writes.
#
# Usage: ./failures.sh [log dir]   (default: ./logs). Needs REDIS_PASSWORD in the environment.
set -u
cd /workspaces/databases_module/exercises/16-consistency/challenge
unset REDIS_URL DATABASE_URL
export REDISCLI_AUTH="$REDIS_PASSWORD"
L=${1:-logs}; mkdir -p "$L"; : > $L/worker.log; : > $L/rent.log; : > $L/events.log
ev(){ echo "[$(date +%H:%M:%S.%3N)] >>> $*" | tee -a $L/events.log >> $L/worker.log; }
E="uv run --env-file .env python"
wait_line(){ # wait until the last line of worker.log contains $1
  for i in $(seq 1 400); do tail -n1 $L/worker.log | grep -q "$1" && return 0; sleep 0.05; done; return 1; }

$E worker.py --pause 0.3 >> $L/worker.log 2>&1 & W1=$!
sleep 1
$E rent.py 5000 --delay 0.002 > $L/rent.log 2>&1 & RENT=$!
sleep 4
WP=$(pgrep -f 'bin/python[0-9.]* worker.py' | head -1)
wait_line "redis updated" && { ev "kill -9 $WP (worker)"; kill -9 $WP; }
wait $W1 2>/dev/null
sleep 1
ev "worker started again"
$E worker.py --pause 0.3 --exit-when-idle 5 >> $L/worker.log 2>&1 & W2=$!
sleep 4
wait_line "claimed" && { ev "docker compose kill redis"; (cd /workspaces/databases_module && docker compose kill redis >/dev/null 2>&1); }
sleep 3
ev "redis starting again (AOF files)"
(cd /workspaces/databases_module && docker compose -f docker-compose.yml -f docker-compose.redis-aof.yml up -d redis >/dev/null 2>&1)
# no --wait (it waits for the 5 s healthcheck): retry CONFIG SET until Redis answers
until redis-cli -h redis CONFIG SET appendfsync always 2>/dev/null | grep -q OK; do sleep 0.02; done
ev "redis up, CONFIG SET appendfsync always"
wait $RENT; wait $W2
ev "worker finished"
