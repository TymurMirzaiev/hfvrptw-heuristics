# Results

The raw output of every run behind papers [7] and [8]: 9032 runs. Each solution was re-checked by the independent checker (`hfvrptw/checker.py`) and none violates any constraint.

| File | What it is |
|---|---|
| `raw/<experiment>.jsonl` | one line per run (format below) |
| `summary.json` | all tables of both papers, computed from `raw/` by `scripts/analyze_results.py` |
| `descent_times.json` | time of one local search descent (M4) per own instance, median of 5 measurements; used to set the relative budgets of `p7_rel` |

## Experiments

| File in `raw/` | Paper | What was run | Runs |
|---|---|---|---|
| `p7_own.jsonl` | [7] | methods M1–M6 on the 18 own instances. M1–M4 run once. M5 and M6 run with a small budget (1/2/4 s) and a large one (3/6/12 s), 10 seeds each | 792 |
| `p7_rel.jsonl` | [7] | M5 and M6 with budgets of 0.5, 1, 2, 5, 10 and 50 × the descent time of the instance, 10 seeds | 2160 |
| `p7_ls.jsonl` | [7] | M1–M6 on the 56 Liu & Shen instances. M5 and M6 run with 4 s and 12 s, 5 seeds | 1344 |
| `p8_ls.jsonl` | [8] | type change strategies C0–C5 in local search run to convergence, with the cost lower bound, 10 seeds | 1080 |
| `p8_ils.jsonl` | [8] | C0–C5 inside iterated local search under 1/2/4 s, with the cost lower bound, 10 seeds | 1080 |
| `p8_ls_naive.jsonl` | [8] | the same as `p8_ls`, but every move is evaluated in full (no lower bound) | 1080 |
| `p8_ils_naive.jsonl` | [8] | the same as `p8_ils`, without the lower bound | 1080 |
| `p8_liu.jsonl` | [8] | C0–C5 in iterated local search under 4 s on 12 Liu & Shen instances with 3–6 vehicle types, 5 seeds | 360 |
| `sanity.jsonl` | — | single-type VRPTW on the 56 Solomon instances, iterated local search 20 s | 56 |

## Line format (`raw/*.jsonl`)

```json
{"inst": "R25_0", "n": 25, "exp": "p7_own", "family": "own", "method": "M6",
 "budget": 1.0, "bname": "small", "seed": 0,
 "cost": 1107.32, "ok": true, "viol": [], "fleet": [0, 4, 1], "vehicles": 5,
 "dist": 756.37, "time": 1.0, "iters": 197,
 "routes": [[1, [24, 15, 9, 2, 14]], [1, [6, 25, 12, 20, 8, 18, 3]], ...]}
```

| Field | Meaning |
|---|---|
| `inst`, `n` | instance name, number of customers |
| `exp`, `family`, `method`, `strategy`, `budget`, `bname`, `rel`, `seed` | what was run: experiment (the `_naive` experiments are the runs without the lower bound), instance set (`own`, `liu`, `sol`), method (`M1`…`M6`, `LS`, `ILS`), type change strategy (`C0`…`C5`), time budget in seconds, budget label (`small`/`large`), relative budget (× descent time, `p7_rel` only), random seed |
| `cost` | plan cost **recomputed by the checker** from the routes |
| `ok`, `viol` | checker verdict and list of violations (always `true` and empty here) |
| `fleet`, `vehicles` | vehicles used per type (truck, van, bike), total |
| `dist`, `time` | total distance; running time in seconds |
| `routes` | the full plan: `[type index, [customers in visiting order]]` per route |
| `key`, `spec` | internal run identifier (used to resume interrupted experiments) and generator arguments of an own instance |
| `evals`, `type_evals`, `type_changes`, `passes`, `iters`, `starts`, `ls_time` | counters, where relevant: route evaluations, of which spent on trying vehicle types, accepted type changes, local search passes, ILS iterations, multistart starts, time of the local search descent |

## How quality is measured

- **Own instances:** relative gap (%) to the best cost found for that instance in any run of this repository (`ref` in `summary.json`).
- **Liu & Shen:** gap to the best-known solution in `../data/liu_shen/bks.csv`.
- **Solomon sanity check:** gap to the PyVRP best-known distance. That distance is computed with rounding; here distances are not rounded.
- **Statistics:** two-sided Wilcoxon signed-rank test on per-instance means, with Holm correction within each family of comparisons.

Time budgets are wall-clock seconds on one core, so absolute times depend on the machine. The relative budgets of `p7_rel` and the evaluation counts of paper [8] do not.
