# HFVRPTW heuristics

**Delivery planning with a mixed fleet (trucks, vans, cargo bikes) and customer time windows.**
This repository holds the code, test instances and raw results behind two papers:
- which routing method to run when you have only a few seconds;
- how a heuristic should choose the vehicle type of each route.

Pure Python, no external solver. Українською — [нижче](#українською).

**Contents:**
- [The problem](#the-problem)
- [Main results](#main-results)
- [Quick start](#quick-start)
- [Repository structure](#repository-structure)
- [Reproduce the papers](#reproduce-the-papers)
- [Citation](#citation)
- [Contact](#contact)

---

## The problem

A depot serves customers. Each customer has:
- an order with a weight and a volume;
- a time window in which delivery must start;
- a service time.

The fleet has three vehicle types, and you can use as many vehicles of each type as you like:

| Type | Payload | Volume | Fixed cost | Cost per km | Speed |
|---|---|---|---|---|---|
| 🚚 truck | 200 | 60 | 180 | 1.40 | 0.85 |
| 🚐 van | 100 | 32 | 100 | 1.00 | 1.00 |
| 🚲 cargo bike | 30 | 9 | 35 | 0.45 | 0.70 |

**Goal:** the cheapest set of routes that serves every customer on time. A route costs fixed cost + cost per km × length.

**Why it is hard:** the vehicle type of a route changes both its cost **and** its speed. So the type also decides whether the time windows can be met. In practice the planner also has a fixed time budget for the computation.

## Main results

| Paper | Question | Answer |
|---|---|---|
| **[7] Method selection** | Six methods, from nearest neighbour to iterated local search: which one for which time budget? | **Local search gives the biggest single gain.** Adding it to insertion cuts the mean gap from 42.2 % to 17.6 %. **A metaheuristic pays off only if the budget is at least 2× the time of one local search descent.** With 5× or more, iterated local search beats plain local search on every instance. On the public Liu & Shen benchmark, the best method is 5.5 % above the best-known solutions after 12 s. |
| **[8] Type change operator** | When should local search try other vehicle types for a route? | **Evaluated naively, trying all types is expensive**: 1.63× the route evaluations. **With a constant-time cost bound per type it becomes almost free**: 1.03×, with 97.6 % fewer evaluations. It then gives the best solutions. Re-typing a finished solution afterwards brings no gain. |

Authors: T. R. Mirzaiev, H. Y. Mykhalchuk (Oles Honchar Dnipro National University). Both papers are in Ukrainian and have been submitted to Ukrainian scientific journals. Details: [`docs/methods.md`](docs/methods.md).

## Quick start

You need Python 3.9 or newer. The solver itself uses only the standard library. Install the requirements only to rerun the analysis and the figures.

```bash
git clone https://github.com/TymurMirzaiev/hfvrptw-heuristics.git
cd hfvrptw-heuristics
python3 examples/solve.py data/own/RC100_0.json --method M6 --time 4
```

```
RC100_0: 100 customers, method M6, 4.0 s
cost 3192.7 | vehicles 13 (truck 6, van 4, bike 3) | checker: ok
```

| Option | Values |
|---|---|
| `--method` | `M1` nearest neighbour · `M2` savings · `M3` insertion · `M4` insertion + local search · `M5` multistart · `M6` iterated local search |
| `--time` | time budget in seconds (for M5 and M6) |
| `--seed` | random seed |
| `--out plan.json` | save the routes |

Using the code from Python: see [`docs/methods.md`](docs/methods.md#using-the-code).

## Repository structure

```
hfvrptw-heuristics/
├── hfvrptw/                 the solver (Python package)
│   ├── instance.py          instances: generator, Solomon and Liu & Shen readers
│   ├── core.py              route evaluation, cheapest feasible type, cost lower bound
│   ├── construct.py         M1 nearest neighbour, M2 savings, M3 insertion
│   ├── ls.py                local search with type change strategies C0–C5
│   ├── meta.py              M4, M5 multistart, M6 iterated local search
│   └── checker.py           independent feasibility checker
├── examples/
│   └── solve.py             solve one instance from the command line
├── scripts/                 everything needed to reproduce the papers
│   ├── run_experiments.py   run one experiment → results/raw/<experiment>.jsonl
│   ├── run_all.sh           run all experiments in sequence
│   ├── analyze_results.py   tables and statistics → results/summary.json
│   ├── make_figures.py      figures → figures/
│   └── export_instances.py  regenerate data/own/
├── data/                    test instances — see data/README.md
│   ├── own/                 our 18 instances (.json + readable .txt)
│   ├── liu_shen/            Liu & Shen vehicle types and best-known solutions
│   └── solomon/             Solomon's 56 VRPTW instances (PyVRP collection)
├── results/                 raw results of all 9032 runs — see results/README.md
│   ├── raw/                 one .jsonl file per experiment
│   ├── summary.json         all tables of both papers
│   └── descent_times.json   local search descent time per instance
├── figures/                 figures of the papers
├── docs/
│   └── methods.md           methods, strategies, code map, API example
├── CITATION.cff
└── requirements.txt
```

## Reproduce the papers

Run all commands from the repository root.

```bash
pip install -r requirements.txt

sh scripts/run_all.sh                        # all experiments: about 5 hours on 2 cores
python3 scripts/analyze_results.py           # prints the tables, writes results/summary.json
python3 scripts/make_figures.py              # writes figures/*.png
```

- **One experiment only:** `python3 scripts/run_experiments.py p7_own 2`. The last argument is the number of worker processes.
- **Experiments and what each one runs:** [`results/README.md`](results/README.md).
- **Resuming:** runs already in a result file are skipped, so an interrupted experiment continues where it stopped. To start from scratch, delete the file first.
- **Re-analysing without rerunning:** the published raw results are already in `results/raw/`, so `analyze_results.py` reproduces every table of both papers right away.

**Trust but verify.**
- Every solution is re-checked by [`hfvrptw/checker.py`](hfvrptw/checker.py). It shares no code with the methods and recomputes loads, arrival times, time windows and cost from the raw data.
- All 9032 published solutions pass, with no violations.
- Every route of every solution is stored in `results/raw/`, so any number can be checked independently.

## Citation

If you use the code or the instances, please cite the repository (see [`CITATION.cff`](CITATION.cff)). Once the papers are published, cite them too:

- [7] Mirzaiev T. R., Mykhalchuk H. Y. Comparative analysis of solution methods for the heterogeneous fleet vehicle routing problem with time windows. 2026, submitted. (In Ukrainian.)
- [8] Mirzaiev T. R., Mykhalchuk H. Y. The vehicle type change operator in local search for the heterogeneous fleet vehicle routing problem. 2026, submitted. (In Ukrainian.)

Third-party data:
- **Solomon instances:** PyVRP instance collection, MIT licence, [`data/solomon/LICENSE_PyVRP_Instances.txt`](data/solomon/LICENSE_PyVRP_Instances.txt).
- **Liu & Shen best-known solutions:** Koç et al. (2015), see [`data/liu_shen/SOURCES.md`](data/liu_shen/SOURCES.md).

## Contact

Tymur Mirzaiev · Oles Honchar Dnipro National University · timur.mirzaiev@gmail.com · [ORCID 0009-0006-0158-4329](https://orcid.org/0009-0006-0158-4329)

Related: [mt-hfvrptw-stand](https://github.com/TymurMirzaiev/mt-hfvrptw-stand), the multi-objective, multi-trip version of the problem.

---

## Українською

**Що це.** Код, тестові задачі та сирі результати двох статей про планування доставки різнорідним парком (вантажівки, фургони, вантажні велосипеди) з часовими вікнами клієнтів.

| Стаття | Головний висновок |
|---|---|
| **[7] Порівняльний аналіз методів** | Найбільший виграш дає локальний пошук: середній розрив зменшується з 42,2 % до 17,6 %. Метаевристика окупається, лише якщо бюджет часу щонайменше вдвічі перевищує тривалість одного спуску локального пошуку. За п'ятикратного запасу ітерований локальний пошук кращий на всіх задачах. |
| **[8] Оператор зміни типу** | Якщо переміщення відсіювати нижньою оцінкою вартості, повний перебір типів майже нічого не коштує (×1,03 оцінювань замість ×1,63) і дає найкращі розв'язки. Переоптимізація типів у готовому розв'язку виграшу не дає. |

**Як спробувати:**

```bash
python3 examples/solve.py data/own/RC100_0.json --method M6 --time 4
```

**Що де лежить:**
- `hfvrptw/` — методи;
- `data/own/` — 18 тестових задач ([опис формату](data/README.md));
- `data/liu_shen/`, `data/solomon/` — загальнодоступні задачі;
- `results/` — сирі результати всіх 9032 прогонів ([опис](results/README.md));
- `scripts/` — як повторити всі експерименти;
- `docs/methods.md` — опис методів і стратегій.

Усі розв'язки перевірено незалежним контролером допустимості; порушень немає.
