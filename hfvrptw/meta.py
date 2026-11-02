"""Methods M4-M6 of paper [7] and the budgeted ILS used in paper [8]."""
import random

from .construct import insertion, reinsert
from .core import Clock, Counter
from .ls import LS


def m4(inst, strategy="M4", cnt=None):
    """M3 insertion followed by local search to convergence (no time limit)."""
    cnt = cnt or Counter()
    clock = Clock()
    sol = insertion(inst)
    LS(inst, strategy, random.Random(0), cnt).run(sol)
    return sol, clock.elapsed(), cnt


def m5(inst, budget, seed, strategy="M4", cnt=None):
    """Multistart: randomised insertion (one of the 3 best candidates) + local search,
    repeated until the budget is spent; the best solution is returned."""
    rng = random.Random(seed)
    cnt = cnt or Counter()
    clock = Clock(budget)
    best = None
    starts = 0
    while True:
        sol = insertion(inst, rng, rcl=3)
        LS(inst, strategy, rng, cnt, clock).run(sol)
        starts += 1
        if best is None or sol.cost() < best.cost() - 1e-9:
            best = sol
        if clock.out():
            break
    return best, dict(starts=starts, time=clock.elapsed())


def ils(inst, budget, seed, strategy="M4", start=None, cnt=None, bound=True):
    """Iterated local search: remove 10-30 % random customers, greedy reinsertion with
    +-20 % noise, local search; improvements always accepted, deteriorations within 2 %
    with probability 0.3; the best solution is returned."""
    rng = random.Random(seed)
    cnt = cnt or Counter()
    clock = Clock(budget)
    cur = insertion(inst) if start is None else start.copy()
    LS(inst, strategy, rng, cnt, clock, bound).run(cur)
    best = cur.copy()
    iters = 0
    while not clock.out():
        cand = cur.copy()
        k = max(1, int(round(inst.n * rng.uniform(0.10, 0.30))))
        allc = [u for r in cand.routes for u in r.seq]
        rem = set(rng.sample(allc, min(k, len(allc))))
        for r in cand.routes:
            r.seq = [u for u in r.seq if u not in rem]
        for r in cand.routes:
            from .core import loads, route_len, route_eval
            r.m, r.vol = loads(inst, r.seq)
            r.L = route_len(inst, r.seq)
            r.cost = route_eval(inst, r.seq, r.k) if r.seq else 0.0
        cand.clean()
        order = list(rem)
        rng.shuffle(order)
        reinsert(inst, cand, order, rng, 0.2, cnt)
        LS(inst, strategy, rng, cnt, clock, bound).run(cand)
        iters += 1
        cc, cu = cand.cost(), cur.cost()
        if cc < cu - 1e-9 or (cc <= cu * 1.02 and rng.random() < 0.3):
            cur = cand
        if cur.cost() < best.cost() - 1e-9:
            best = cur.copy()
    return best, dict(iters=iters, time=clock.elapsed())
