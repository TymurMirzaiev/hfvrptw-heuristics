"""Experiment runner for papers [7] (method selection) and [8] (type change operator).

usage: python3 scripts/run_experiments.py <experiment> [workers]   (from the repository root)
Each run appends one JSON line to results/raw/<experiment>.jsonl; runs already present
are skipped, so an interrupted experiment resumes where it stopped.

experiments:
  p7_own      M1-M6 on the 18 own instances; M5/M6 with budgets 1/2/4 s and 3/6/12 s, 10 seeds
  p7_rel      M5/M6 on the 18 own instances with budgets = x * (descent time of M4), 10 seeds
  p7_ls       M1-M6 on Liu-Shen (cost structure A, 56 instances), M5/M6 4 s and 12 s, 5 seeds
  p8_ls       strategies C0-C5 in local search to convergence from M3, 18 own instances, 10 seeds
  p8_ils      strategies C0-C5 in ILS under 1/2/4 s, 18 own instances, 10 seeds
  p8_ls_naive, p8_ils_naive  the same two experiments with naive evaluation (no cost lower bound)
  p8_liu      strategies C0-C5 in ILS under 4 s on 12 Liu-Shen instances (3-6 types), 5 seeds
  sanity      single-type VRPTW special case on all 56 Solomon instances, ILS 20 s
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import json
import time
import random
from multiprocessing import Pool

from hfvrptw.instance import generate, own_set, liu_shen, solomon_names, solomon_vrptw
from hfvrptw.construct import nearest_neighbour, savings, insertion
from hfvrptw.core import Counter, Clock
from hfvrptw.ls import LS
from hfvrptw.meta import m5, ils
from hfvrptw.checker import check

RES = os.path.join(ROOT, "results")
RAW = os.path.join(RES, "raw")
SMALL = {25: 1.0, 50: 2.0, 100: 4.0}
LARGE = {25: 3.0, 50: 6.0, 100: 12.0}
REL = [0.5, 1, 2, 5, 10, 50]
STRATS = ["C0", "C1", "C2", "C3", "C4", "C5"]
LIU12 = ["R101", "R105", "C101", "C105", "RC101", "RC105",
         "R201", "R205", "C201", "C205", "RC201", "RC205"]


def own(spec):
    c, n, i = spec
    return generate(c, n, i)


def record(inst, sol, extra):
    routes = sol.to_list()
    ok, viol, cost = check(inst, routes, sol.cost())
    fl = sol.fleet(inst)
    out = dict(inst=inst.name, n=inst.n, cost=cost, ok=ok, viol=viol[:3], fleet=fl,
               vehicles=sum(fl), dist=sum(r.L for r in sol.routes), routes=routes)
    out.update(extra)
    return out


def descent(inst, strategy="M4", seed=0):
    """M3 + local search to convergence; returns solution, LS time, counter."""
    sol = insertion(inst)
    cnt = Counter()
    t0 = time.perf_counter()
    LS(inst, strategy, random.Random(seed), cnt).run(sol)
    return sol, time.perf_counter() - t0, cnt


def job(task):
    exp, key = task["exp"], task["key"]
    if task["family"] == "own":
        inst = own(task["spec"])
    elif task["family"] == "liu":
        inst = liu_shen(task["spec"], "A")
    else:
        inst = solomon_vrptw(task["spec"])
    meth = task["method"]
    t0 = time.perf_counter()
    if meth in ("M1", "M2", "M3"):
        sol = {"M1": nearest_neighbour, "M2": savings, "M3": insertion}[meth](inst)
        rec = record(inst, sol, dict(time=time.perf_counter() - t0))
    elif meth == "M4":
        sol, tls, cnt = descent(inst)
        rec = record(inst, sol, dict(time=time.perf_counter() - t0, ls_time=tls, evals=cnt.evals))
    elif meth in ("M5", "M6"):
        f = m5 if meth == "M5" else ils
        sol, info = f(inst, task["budget"], task["seed"])
        info.pop("time", None)
        rec = record(inst, sol, dict(time=time.perf_counter() - t0, **info))
    elif meth == "LS":
        cnt = Counter()
        sol = insertion(inst)
        c0 = time.perf_counter()
        L = LS(inst, task["strategy"], random.Random(task["seed"]), cnt, None, task.get("bound", True))
        L.run(sol)
        rec = record(inst, sol, dict(time=time.perf_counter() - c0, evals=cnt.evals,
                                     type_evals=cnt.type_evals, type_changes=cnt.type_changes,
                                     passes=L.passes))
    elif meth == "ILS":
        cnt = Counter()
        sol, info = ils(inst, task["budget"], task["seed"], task["strategy"], cnt=cnt,
                        bound=task.get("bound", True))
        info.pop("time", None)
        rec = record(inst, sol, dict(time=time.perf_counter() - t0, evals=cnt.evals,
                                     type_evals=cnt.type_evals, type_changes=cnt.type_changes, **info))
    rec.update({k: v for k, v in task.items() if k not in ("spec",)})
    rec["spec"] = task["spec"]
    return rec


def tasks(exp):
    T = []

    def add(**kw):
        kw["exp"] = exp
        kw["key"] = "|".join(str(kw[k]) for k in sorted(kw) if k != "exp")
        T.append(kw)

    if exp == "p7_own":
        for spec in own_set():
            n = spec[1]
            for m in ("M1", "M2", "M3", "M4"):
                add(family="own", spec=spec, method=m)
            for m in ("M5", "M6"):
                for bname, B in (("small", SMALL), ("large", LARGE)):
                    for seed in range(10):
                        add(family="own", spec=spec, method=m, budget=B[n], bname=bname, seed=seed)
    elif exp == "p7_rel":
        desc = descent_times()
        for spec in own_set():
            tl = desc["%s%d_%d" % spec]
            for m in ("M5", "M6"):
                for x in REL:
                    for seed in range(10):
                        add(family="own", spec=spec, method=m, budget=round(x * tl, 4), rel=x, seed=seed)
    elif exp == "p7_ls":
        for nm in solomon_names():
            for m in ("M1", "M2", "M3", "M4"):
                add(family="liu", spec=nm, method=m)
            for m in ("M5", "M6"):
                for bname, B in (("small", 4.0), ("large", 12.0)):
                    for seed in range(5):
                        add(family="liu", spec=nm, method=m, budget=B, bname=bname, seed=seed)
    elif exp == "p8_ls":
        for spec in own_set():
            for s in STRATS:
                for seed in range(10):
                    add(family="own", spec=spec, method="LS", strategy=s, seed=seed)
    elif exp == "p8_ils":
        for spec in own_set():
            for s in STRATS:
                for seed in range(10):
                    add(family="own", spec=spec, method="ILS", strategy=s, budget=SMALL[spec[1]], seed=seed)
    elif exp == "p8_ls_naive":
        for spec in own_set():
            for s in STRATS:
                for seed in range(10):
                    add(family="own", spec=spec, method="LS", strategy=s, seed=seed, bound=False)
    elif exp == "p8_ils_naive":
        for spec in own_set():
            for s in STRATS:
                for seed in range(10):
                    add(family="own", spec=spec, method="ILS", strategy=s, budget=SMALL[spec[1]], seed=seed,
                        bound=False)
    elif exp == "p8_liu":
        for nm in LIU12:
            for s in STRATS:
                for seed in range(5):
                    add(family="liu", spec=nm, method="ILS", strategy=s, budget=4.0, seed=seed)
    elif exp == "sanity":
        for nm in solomon_names():
            add(family="sol", spec=nm, method="M6", budget=20.0, seed=0)
    return T


def descent_times():
    """Median (over 5 repetitions) wall time of the M4 local search descent per own instance."""
    path = os.path.join(RES, "descent_times.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    out = {}
    for spec in own_set():
        inst = own(spec)
        ts = sorted(descent(inst)[1] for _ in range(5))
        out[inst.name] = ts[2]
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    return out


def main():
    exp = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, exp + ".jsonl")
    done = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                done.add(json.loads(line)["key"])
    todo = [t for t in tasks(exp) if t["key"] not in done]
    print("%s: %d runs, %d to do" % (exp, len(todo) + len(done), len(todo)), flush=True)
    with Pool(workers) as pool, open(path, "a") as f:
        for i, rec in enumerate(pool.imap_unordered(job, todo, chunksize=1)):
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if not rec["ok"]:
                print("VIOLATION", rec["inst"], rec["viol"], flush=True)
            if (i + 1) % 50 == 0:
                print("  %d/%d" % (i + 1, len(todo)), flush=True)


if __name__ == "__main__":
    main()
