"""Solve one instance with one method and print the plan summary.

usage: python3 examples/solve.py <instance.json> [--method M1..M6] [--time seconds] [--seed n] [--out plan.json]
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import argparse
import json

from hfvrptw.instance import from_json
from hfvrptw.construct import nearest_neighbour, savings, insertion
from hfvrptw.meta import m4, m5, ils
from hfvrptw.checker import check


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("--method", default="M6", choices=["M1", "M2", "M3", "M4", "M5", "M6"])
    ap.add_argument("--time", type=float, default=4.0, help="budget for M5/M6, seconds")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out")
    a = ap.parse_args()
    inst = from_json(a.instance)
    if a.method == "M1":
        sol = nearest_neighbour(inst)
    elif a.method == "M2":
        sol = savings(inst)
    elif a.method == "M3":
        sol = insertion(inst)
    elif a.method == "M4":
        sol = m4(inst)[0]
    elif a.method == "M5":
        sol = m5(inst, a.time, a.seed)[0]
    else:
        sol = ils(inst, a.time, a.seed)[0]
    routes = sol.to_list()
    ok, viol, cost = check(inst, routes, sol.cost())
    fl = sol.fleet(inst)
    names = [t["name"] for t in inst.types]
    budget = (", %.1f s" % a.time) if a.method in ("M5", "M6") else ""
    print("%s: %d customers, method %s%s" % (inst.name, inst.n, a.method, budget))
    print("cost %.1f | vehicles %d (%s) | checker: %s" % (
        cost, sum(fl), ", ".join("%s %d" % (n, c) for n, c in zip(names, fl)), "ok" if ok else "; ".join(viol)))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(dict(instance=inst.name, method=a.method, cost=cost,
                           routes=[dict(type=names[k], customers=seq) for k, seq in routes]), f, indent=1)
        print("routes saved to", a.out)


if __name__ == "__main__":
    main()
