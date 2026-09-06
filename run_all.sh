#!/bin/sh -eu
# Full benchmark sweep, timestamped, for a scheduled/repeating run.
#
# Local arms (bounded tasks, multi-file project, local report) need no vault and
# no cloud — always run, fully schedulable. The cloud arms (control, hybrid) run
# ONLY when ANTHROPIC_API_KEY is in the env, i.e. when this script is wrapped:
#
#   unset BAO_TOKEN
#   bao-kit with village/cloudkeys:ANTHROPIC_API_KEY=ANTHROPIC_API_KEY -- ./run_all.sh
#
# which also needs the vault unsealed and a valid token — so fully-unattended
# cloud runs require the desktop awake and a fresh `bao-kit login` in the day.
# REPEATS env overrides the repeat count (default 3).
cd "$(dirname "$0")"
mkdir -p results
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG="results/run-$STAMP.log"
K="${REPEATS:-3}"

log() { echo "$@" | tee -a "$LOG"; }

log "=== local-bench sweep $STAMP (repeats=$K) ==="
log ""; log "== bounded tasks =="
python3 bench.py --warm-k "$K" 2>&1 | tee -a "$LOG"
log ""; log "== multi-file project (single vs split) =="
python3 bench_project.py --repeats "$K" 2>&1 | tee -a "$LOG"
log ""; log "== report pipeline (local arm) =="
python3 bench_report.py 2>&1 | tee -a "$LOG"

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  HAIKU="claude-haiku-4-5-20251001"
  log ""; log "== Haiku baseline: bounded tasks =="
  python3 bench.py --models "$HAIKU" --warm-k "$K" 2>&1 | tee -a "$LOG"
  log ""; log "== Haiku baseline: multi-file project =="
  python3 bench_project.py --models "$HAIKU" --repeats "$K" 2>&1 | tee -a "$LOG"
  log ""; log "== cloud control (Haiku solo report) =="
  python3 bench_control.py 2>&1 | tee -a "$LOG"
  log ""; log "== hybrid (local draft + cloud seam-fix) =="
  python3 bench_hybrid.py 2>&1 | tee -a "$LOG"
else
  log ""; log "== cloud arms SKIPPED (no ANTHROPIC_API_KEY; wrap with 'bao-kit with' to include them) =="
fi
log ""; log "=== done -> $LOG ==="
