#!/bin/sh
# Run from the repository root: sh scripts/run_all.sh
# Run every experiment of papers [7] and [8] in sequence (about 5 hours on 2 cores).
set -e
for e in p8_ls p7_own p8_ils p7_rel p8_ls_naive p8_ils_naive p8_liu p7_ls sanity; do
  python3 scripts/run_experiments.py $e 2
done
