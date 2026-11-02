"""Solution representation, route evaluation and type selection.

A route is (seq, k): a list of customers and a vehicle type index. One route
evaluation = one pass over the sequence with capacity, time-window and horizon
checks for one type; the Counter records how many were performed and how many
of them were spent inside a type enumeration (operator of paper [8]).
"""
import time

INF = float("inf")


class Counter:
    __slots__ = ("evals", "type_evals", "type_changes")

    def __init__(self):
        self.evals = 0
        self.type_evals = 0
        self.type_changes = 0


def route_eval(inst, seq, k, cnt=None, in_enum=False):
    """Return the route cost for type k, or INF if infeasible (capacity is checked
    by the caller through loads; here only times are checked).
    For the FT objective (Liu-Shen) the departure from the depot is delayed as much as
    possible without making the route infeasible, which minimises the waiting time."""
    if cnt is not None:
        cnt.evals += 1
        if in_enum:
            cnt.type_evals += 1
    if not seq:
        return 0.0
    d = inst.d
    a, b, s = inst.a, inst.b, inst.s
    v = inst.v[k]
    prev = 0
    t = 0.0
    L = 0.0
    serv = 0.0
    wait = 0.0          # waiting accumulated so far
    slack = INF         # forward time slack of the departure (Savelsbergh)
    for i in seq:
        t += d[prev][i] / v
        L += d[prev][i]
        if t < a[i]:
            wait += a[i] - t
            t = a[i]
        if t > b[i] + 1e-9:
            return INF
        if wait + (b[i] - t) < slack:
            slack = wait + (b[i] - t)
        t += s[i]
        serv += s[i]
        prev = i
    t += d[prev][0] / v
    L += d[prev][0]
    if t > inst.H + 1e-9:
        return INF
    if inst.objective == "enroute":
        shift = min(wait, slack)
        return inst.F[k] + (t - shift - serv)
    return inst.F[k] + inst.c[k] * L


def route_len(inst, seq):
    d = inst.d
    prev, L = 0, 0.0
    for i in seq:
        L += d[prev][i]
        prev = i
    return L + d[prev][0]


def loads(inst, seq):
    m = v = 0.0
    for i in seq:
        m += inst.q[i]
        v += inst.vol[i]
    return m, v


def cap_ok(inst, k, m, vol):
    return m <= inst.Q[k] + 1e-9 and vol <= inst.W[k] + 1e-9


def lower_bound(inst, k, L):
    """Cost lower bound of a route of length L on type k (exact for 'cost')."""
    if inst.objective == "enroute":
        return inst.F[k] + L          # speed 1: en-route time >= distance
    return inst.F[k] + inst.c[k] * L


def best_type(inst, seq, m, vol, L, cnt=None, in_enum=True, types=None):
    """Cheapest feasible type for a sequence. Types are tried in increasing order of the
    lower bound; for both objectives here the first feasible one is optimal when all types
    share the same speed (Liu-Shen) or when the bound is exact ('cost')."""
    cand = []
    for k in (range(inst.K) if types is None else types):
        if cap_ok(inst, k, m, vol):
            cand.append((lower_bound(inst, k, L), k))
    cand.sort()
    best, bk = INF, -1
    for lb, k in cand:
        if lb >= best - 1e-9:
            break
        c = route_eval(inst, seq, k, cnt, in_enum)
        if c < best:
            best, bk = c, k
    return best, bk


class Route:
    __slots__ = ("seq", "k", "m", "vol", "L", "cost")

    def __init__(self, inst, seq, k, cost=None):
        self.seq = list(seq)
        self.k = k
        self.m, self.vol = loads(inst, seq)
        self.L = route_len(inst, seq)
        self.cost = route_eval(inst, seq, k) if cost is None else cost

    def copy(self):
        r = Route.__new__(Route)
        r.seq = list(self.seq)
        r.k, r.m, r.vol, r.L, r.cost = self.k, self.m, self.vol, self.L, self.cost
        return r


class Sol:
    def __init__(self, routes=None):
        self.routes = routes or []

    def cost(self):
        return sum(r.cost for r in self.routes)

    def copy(self):
        return Sol([r.copy() for r in self.routes])

    def clean(self):
        self.routes = [r for r in self.routes if r.seq]

    def fleet(self, inst):
        cnt = [0] * inst.K
        for r in self.routes:
            cnt[r.k] += 1
        return cnt

    def to_list(self):
        return [[r.k, list(r.seq)] for r in self.routes]


class Clock:
    def __init__(self, budget=None):
        self.t0 = time.perf_counter()
        self.budget = budget

    def elapsed(self):
        return time.perf_counter() - self.t0

    def out(self):
        return self.budget is not None and time.perf_counter() - self.t0 >= self.budget
