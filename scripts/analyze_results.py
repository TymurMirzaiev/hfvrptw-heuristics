"""Aggregate raw results into the tables of papers [7] and [8].

usage: python3 scripts/analyze_results.py            -> prints tables, writes results/summary.json

Quality measure on the own instances: relative gap (%) to the best cost found for the
instance in ANY run of ANY experiment of this repository (pooled reference), so that the
tables of both papers are comparable. On Liu-Shen instances: gap to the best-known
solution from the literature (data/liu_shen/bks.csv).
Statistics: two-sided Wilcoxon signed-rank test on per-instance means (n = number of
instances), Holm correction within each family of comparisons.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import json
from collections import defaultdict
from statistics import mean, pstdev

from scipy.stats import wilcoxon

from hfvrptw.instance import liu_shen_bks

RES = os.path.join(ROOT, "results")
TYPES = ["truck", "van", "bike"]


def load(exp):
    path = os.path.join(RES, "raw", exp + ".jsonl")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(l) for l in f]


def holm(pvals):
    """pvals: dict name -> p. Returns dict name -> adjusted p."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        run = max(run, adj)
        out[k] = run
    return out


def wtest(a, b):
    """Paired two-sided Wilcoxon on dicts inst -> value (common keys)."""
    keys = sorted(set(a) & set(b))
    x = [a[k] for k in keys]
    y = [b[k] for k in keys]
    if all(abs(u - v) < 1e-12 for u, v in zip(x, y)):
        return 1.0
    return float(wilcoxon(x, y, zero_method="wilcox", alternative="two-sided").pvalue)


def ref_costs(*sets):
    best = {}
    for runs in sets:
        for r in runs:
            if r["ok"]:
                best[r["inst"]] = min(best.get(r["inst"], 1e18), r["cost"])
    return best


def gap(c, ref):
    return 100.0 * (c / ref - 1.0)


def group(runs, keyf):
    g = defaultdict(list)
    for r in runs:
        g[keyf(r)].append(r)
    return g


def per_inst_mean(runs, f):
    d = defaultdict(list)
    for r in runs:
        d[r["inst"]].append(f(r))
    return {k: mean(v) for k, v in d.items()}


def by_n(mg):
    """Mean of per-instance values grouped by instance size (name like R25_0, RC100_1)."""
    out = {}
    for n in (25, 50, 100):
        v = [x for k, x in mg.items() if k.split("_")[0].lstrip("RC") == str(n)]
        if v:
            out[n] = mean(v)
    return out


def fmt(x, n=2):
    return ("%." + str(n) + "f") % x


def main():
    out = {}
    p7 = load("p7_own")
    p7rel = load("p7_rel")
    p7ls = load("p7_ls")
    p8ls = load("p8_ls")
    p8ils = load("p8_ils")
    p8liu = load("p8_liu")
    san = load("sanity")
    allruns = p7 + p7rel + p8ls + p8ils + load("p8_ls_naive") + load("p8_ils_naive")
    bad = [r for r in allruns + p7ls + p8liu + san if not r["ok"]]
    out["checked_solutions"] = len(allruns + p7ls + p8liu + san)
    out["violations"] = len(bad)
    print("checked solutions:", out["checked_solutions"], "violations:", len(bad))
    ref = ref_costs(allruns)
    out["ref"] = ref

    # ------------------------------------------------------------- paper [7]
    if p7:
        def mkey(r):
            return r["method"] + ("" if r["method"] in ("M1", "M2", "M3", "M4") else "_" + r["bname"])
        G = group(p7, mkey)
        order = ["M1", "M2", "M3", "M4", "M5_small", "M6_small", "M5_large", "M6_large"]
        tab = {}
        means = {}
        print("\n[7] Table: means over 18 own instances")
        print("method      gap%   veh   dist    time  truck van bike  (shares %)")
        for k in order:
            if k not in G:
                continue
            rs = G[k]
            mg = per_inst_mean(rs, lambda r: gap(r["cost"], ref[r["inst"]]))
            means[k] = mg
            fl = [sum(r["fleet"][i] for r in rs) for i in range(3)]
            tot = sum(fl)
            sh = [100.0 * x / tot for x in fl]
            row = dict(gap=mean(mg.values()), vehicles=mean(r["vehicles"] for r in rs),
                       dist=mean(r["dist"] for r in rs), time=mean(r["time"] for r in rs),
                       shares=sh,
                       gap_by_n=by_n(mg))
            if k == "M4":
                row["ls_time"] = mean(r["ls_time"] for r in rs)
                row["ls_time_by_n"] = {n: mean(r["ls_time"] for r in rs if r["n"] == n) for n in (25, 50, 100) if any(r["n"] == n for r in rs)}
            tab[k] = row
            print("%-10s %6s %5s %7s %7s  %s" % (k, fmt(row["gap"]), fmt(row["vehicles"], 1), fmt(row["dist"], 1),
                                               fmt(row["time"], 3), " ".join(fmt(x, 1) for x in sh)))
        print("gap by size:")
        for k in order:
            if k in tab:
                print("  %-10s %s" % (k, "  ".join(fmt(v) for v in tab[k]["gap_by_n"].values())))
        comps = {
            "M3_vs_M4": ("M3", "M4"), "M1_vs_M3": ("M1", "M3"), "M2_vs_M3": ("M2", "M3"),
            "M5s_vs_M6s": ("M5_small", "M6_small"), "M5l_vs_M6l": ("M5_large", "M6_large"),
            "M4_vs_M5s": ("M4", "M5_small"), "M4_vs_M6s": ("M4", "M6_small"),
            "M6s_vs_M6l": ("M6_small", "M6_large"), "M5s_vs_M5l": ("M5_small", "M5_large"),
        }
        pv = {c: wtest(means[a], means[b]) for c, (a, b) in comps.items() if a in means and b in means}
        ph = holm(pv)
        print("Wilcoxon (raw / Holm):")
        for c in pv:
            print("  %-12s %.4g / %.4g" % (c, pv[c], ph[c]))
        # variability across seeds
        var = {}
        for k in ("M5_small", "M6_small", "M5_large", "M6_large"):
            if k in G:
                d = defaultdict(list)
                for r in G[k]:
                    d[r["inst"]].append(r["cost"])
                var[k] = mean(100.0 * pstdev(v) / mean(v) for v in d.values())
        print("mean coefficient of variation over seeds, %:", {k: round(v, 2) for k, v in var.items()})
        out["p7"] = dict(table=tab, p=pv, p_holm=ph, cv=var)

    if p7rel and p7:
        G = group(p7rel, lambda r: (r["method"], r["rel"]))
        m4 = per_inst_mean([r for r in p7 if r["method"] == "M4"], lambda r: gap(r["cost"], ref[r["inst"]]))
        rel = {}
        print("\n[7] relative budgets (x descent time): mean gap; p vs M4 (raw)")
        for (m, x), rs in sorted(G.items()):
            mg = per_inst_mean(rs, lambda r: gap(r["cost"], ref[r["inst"]]))
            p = wtest(mg, m4)
            wins = sum(1 for k in mg if mg[k] < m4[k] - 1e-9)
            rel["%s_%g" % (m, x)] = dict(gap=mean(mg.values()), p=p, wins=wins,
                                        gap_by_n=by_n(mg))
            print("  %s x=%-4g gap %6s  p=%.3g  better than M4 on %d/18" % (m, x, fmt(mean(mg.values())), p, wins))
        print("  M4 gap", fmt(mean(m4.values())))
        out["p7_rel"] = rel

    if p7ls:
        bks = liu_shen_bks("A")
        G = group(p7ls, lambda r: r["method"] + ("" if r["method"] in ("M1", "M2", "M3", "M4") else "_" + r["bname"]))
        res = {}
        print("\n[7] Liu-Shen (A, 56 instances): mean gap to BKS, % (by class)")
        for k in ["M1", "M2", "M3", "M4", "M5_small", "M6_small", "M5_large", "M6_large"]:
            if k not in G:
                continue
            mg = per_inst_mean(G[k], lambda r: gap(r["cost"], bks[r["spec"]]))
            bycls = defaultdict(list)
            for inst, v in mg.items():
                c = inst[:-1]
                cls = "RC" + c[2] if c.startswith("RC") else c[0] + c[1]
                bycls[cls].append(v)
            res[k] = dict(gap=mean(mg.values()), by_class={c: mean(v) for c, v in sorted(bycls.items())},
                          time=mean(r["time"] for r in G[k]), n=len(mg))
            print("  %-10s %6s  %s" % (k, fmt(res[k]["gap"]), "  ".join("%s %s" % (c, fmt(v)) for c, v in sorted(res[k]["by_class"].items()))))
        out["p7_liu"] = res

    # ------------------------------------------------------------- paper [8]
    def strat_table(runs, refd, title, budget=False):
        G = group(runs, lambda r: r["strategy"])
        tab, means = {}, {}
        print("\n" + title)
        print("strat  gap%   evals      type%   changes  time   veh")
        for s in ["C0", "C2", "C3", "C4", "C5", "C1"]:
            if s not in G:
                continue
            rs = G[s]
            mg = per_inst_mean(rs, lambda r: gap(r["cost"], refd[r["inst"]] if isinstance(refd, dict) and r["inst"] in refd else refd[r["spec"]]))
            means[s] = mg
            ev = mean(r["evals"] for r in rs)
            te = 100.0 * sum(r["type_evals"] for r in rs) / max(1, sum(r["evals"] for r in rs))
            row = dict(gap=mean(mg.values()), evals=ev, type_share=te,
                       changes=mean(r["type_changes"] for r in rs), time=mean(r["time"] for r in rs),
                       vehicles=mean(r["vehicles"] for r in rs))
            if "passes" in rs[0]:
                row["passes"] = mean(r["passes"] for r in rs)
            if "iters" in rs[0]:
                row["iters"] = mean(r["iters"] for r in rs)
            tab[s] = row
            print("%-5s %6s %10s %7s %8s %6s %5s" % (s, fmt(row["gap"]), fmt(ev, 0), fmt(te, 1),
                                                   fmt(row["changes"], 1), fmt(row["time"], 3), fmt(row["vehicles"], 1)))
        pv = {}
        for s in tab:
            if s != "C0":
                pv["%s_vs_C0" % s] = wtest(means[s], means["C0"])
            if s not in ("C1", "C0"):
                pv["%s_vs_C1" % s] = wtest(means[s], means["C1"])
        ph = holm(pv)
        print("Wilcoxon raw / Holm:", {k: "%.3g/%.3g" % (pv[k], ph[k]) for k in sorted(pv)})
        return dict(table=tab, p=pv, p_holm=ph)

    if p8ls:
        out["p8_ls"] = strat_table(p8ls, ref, "[8] local search to convergence (18 own instances x 10 seeds)")
    if p8ils:
        out["p8_ils"] = strat_table(p8ils, ref, "[8] ILS under 1/2/4 s (18 own instances x 10 seeds)")
    p8lsn = load("p8_ls_naive")
    p8ilsn = load("p8_ils_naive")
    if p8lsn:
        out["p8_ls_naive"] = strat_table(p8lsn, ref, "[8] NAIVE local search to convergence")
    if p8ilsn:
        out["p8_ils_naive"] = strat_table(p8ilsn, ref, "[8] NAIVE ILS under 1/2/4 s")
    if p8liu:
        out["p8_liu"] = strat_table(p8liu, liu_shen_bks("A"), "[8] ILS 4 s on 12 Liu-Shen instances (gap to BKS)")

    if san:
        from hfvrptw.instance import solomon_bks
        g = [gap(r["cost"], solomon_bks(r["spec"])) for r in san]
        out["sanity"] = dict(n=len(g), mean_gap=mean(g), median_gap=sorted(g)[len(g) // 2])
        print("\nSolomon VRPTW sanity check: %d instances, mean gap %.2f %%, median %.2f %%" %
              (len(g), mean(g), sorted(g)[len(g) // 2]))

    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
