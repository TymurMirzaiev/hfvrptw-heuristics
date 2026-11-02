"""Figures of papers [7] and [8] (PNG, 300 dpi) from results/summary.json.

usage: python3 scripts/analyze_results.py && python3 scripts/make_figures.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RES = os.path.join(ROOT, "results")
FIG = os.path.join(ROOT, "figures")
plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 10})


def fig7(s):
    rel = s["p7_rel"]
    m4 = s["p7"]["table"]["M4"]["gap"]
    xs = sorted({float(k.split("_")[1]) for k in rel})
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for m, mk, lab in (("M5", "s--", "M5 (багаторазовий старт)"), ("M6", "o-", "M6 (ітерований локальний пошук)")):
        ys = [rel["%s_%g" % (m, x)]["gap"] for x in xs]
        ax.plot(xs, ys, mk, color="black", lw=1.2, ms=4, label=lab)
    ax.axhline(m4, color="black", lw=1, ls=":", label="M4 (вставка + локальний пошук)")
    ax.axvspan(xs[0] * 0.9, 2, color="0.9", zorder=0)
    ax.set_xscale("log")
    ax.set_xticks(xs)
    ax.set_xticklabels(["%g" % x for x in xs])
    ax.set_xlabel("Бюджет часу / тривалість одного спуску локального пошуку")
    ax.set_ylabel("Середній відносний розрив, %")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "p7_fig1_budget.png"), dpi=300)
    plt.close(fig)


def fig8(s):
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.0), sharey=False)
    labels = {"C0": "С0", "C1": "С1", "C2": "С2", "C3": "С3", "C4": "С4", "C5": "С5"}
    panels = [("p8_ls", "p8_ls_naive", "а) локальний пошук до збіжності"),
              ("p8_ils", "p8_ils_naive", "б) ітерований пошук під бюджетом")]
    for ax, (kb, kn, title) in zip(axes, panels):
        series = []
        for key, mk, lab in ((kn, "s", "без нижньої оцінки"), (kb, "o", "з нижньою оцінкою")):
            if key not in s:
                continue
            t = s[key]["table"]
            order = sorted(t, key=lambda c: t[c]["type_share"])
            xs = [t[c]["type_share"] for c in order]
            ys = [t[c]["gap"] for c in order]
            ax.plot(xs, ys, mk + "-", color="black", mfc="white" if mk == "s" else "black", lw=1, ms=4, label=lab)
            series.append(list(zip(order, xs, ys)))
        # label every point once; points closer than ~2.5 % of the axis span share one label,
        # and neighbours within one series are pushed apart vertically
        allpts = [p for ser in series for p in ser]
        yspan = (max(p[2] for p in allpts) - min(p[2] for p in allpts)) or 1.0
        placed = []
        for ser in series:
            for c, x, y in ser:
                if any(c == pc and abs(x - px) < 6 and abs(y - py) < 0.04 * yspan for pc, px, py, _ in placed):
                    continue
                near = sum(1 for pc, px, py, _ in placed if abs(x - px) < 6 and abs(y - py) < 0.06 * yspan)
                off = (4, 3 - 9 * near)
                placed.append((c, x, y, off))
                ax.annotate(labels[c], (x, y), textcoords="offset points", xytext=off, fontsize=7)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("Частка оцінювань на перебір типів, %")
    axes[0].set_ylabel("Середній відносний розрив, %")
    axes[0].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "p8_fig1_share.png"), dpi=300)
    plt.close(fig)


def main():
    os.makedirs(FIG, exist_ok=True)
    with open(os.path.join(RES, "summary.json")) as f:
        s = json.load(f)
    if "p7_rel" in s:
        fig7(s)
    if "p8_ls" in s:
        fig8(s)


if __name__ == "__main__":
    main()
