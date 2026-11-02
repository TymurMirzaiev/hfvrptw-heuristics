"""Constructive methods of paper [7] (M1 nearest neighbour, M2 savings, M3 insertion
with type choice) and the insertion machinery reused by the metaheuristics."""
import random

from .core import INF, Route, Sol, best_type, cap_ok, route_eval, loads, route_len


# ------------------------------------------------------------ time-window caches

def tw_arrays(inst, seq, k):
    """Earliest service starts (departure from the depot at time 0) and latest service
    starts that keep the rest of the route feasible, for type k."""
    d, a, b, s, v = inst.d, inst.a, inst.b, inst.s, inst.v[k]
    n = len(seq)
    st = [0.0] * n
    t, prev = 0.0, 0
    ok = True
    for p, i in enumerate(seq):
        t += d[prev][i] / v
        if t < a[i]:
            t = a[i]
        if t > b[i] + 1e-9:
            ok = False
        st[p] = t
        t += s[i]
        prev = i
    if t + d[prev][0] / v > inst.H + 1e-9:
        ok = False
    lat = [0.0] * n
    nxt_lat = inst.H
    nxt = 0
    for p in range(n - 1, -1, -1):
        i = seq[p]
        lim = nxt_lat - d[i][nxt] / v - s[i]
        lat[p] = min(b[i], lim)
        nxt_lat, nxt = lat[p], i
    return ok, st, lat


class RouteCache:
    """Per-route, per-type time-window arrays, computed lazily."""

    def __init__(self, inst):
        self.inst = inst
        self.data = {}

    def get(self, r, k):
        key = (id(r), k)
        e = self.data.get(key)
        if e is None or e[0] is not r.seq or e[1] != len(r.seq):
            ok, st, lat = tw_arrays(self.inst, r.seq, k)
            e = (r.seq, len(r.seq), ok, st, lat)
            self.data[key] = e
        return e[2], e[3], e[4]

    def drop(self, r):
        for k in range(self.inst.K):
            self.data.pop((id(r), k), None)


def ins_feasible(inst, seq, st, lat, k, u, p):
    """Can customer u be inserted at position p (before seq[p]) on type k?"""
    d, a, b, s, v = inst.d, inst.a, inst.b, inst.s, inst.v[k]
    if p == 0:
        prev, e = 0, 0.0
    else:
        prev = seq[p - 1]
        e = st[p - 1] + s[prev]
    tu = e + d[prev][u] / v
    if tu < a[u]:
        tu = a[u]
    if tu > b[u] + 1e-9:
        return False
    if p == len(seq):
        return tu + s[u] + d[u][0] / v <= inst.H + 1e-9
    j = seq[p]
    tj = tu + s[u] + d[u][j] / v
    if tj < a[j]:
        tj = a[j]
    return tj <= lat[p] + 1e-9


def proxy(inst, k, L):
    return inst.F[k] + inst.c[k] * L


def insertion_options(inst, cache, r, u, types_all=True):
    """Best (delta, p, k) for inserting u into route r; with types_all the type may change."""
    seq = r.seq
    m = r.m + inst.q[u]
    vol = r.vol + inst.vol[u]
    d = inst.d
    old = proxy(inst, r.k, r.L)
    ks = range(inst.K) if types_all else (r.k,)
    best = (INF, -1, -1)
    for k in ks:
        if not cap_ok(inst, k, m, vol):
            continue
        ok, st, lat = cache.get(r, k)
        if not ok:
            continue
        prev = 0
        for p in range(len(seq) + 1):
            nxt = seq[p] if p < len(seq) else 0
            dl = d[prev][u] + d[u][nxt] - d[prev][nxt]
            delta = proxy(inst, k, r.L + dl) - old
            if delta < best[0] and ins_feasible(inst, seq, st, lat, k, u, p):
                best = (delta, p, k)
            prev = nxt
    return best


def new_route_option(inst, u):
    """Cheapest type for a single-customer route."""
    c, k = best_type(inst, [u], inst.q[u], inst.vol[u], 2 * inst.d[0][u], None, False)
    return c, k


def apply_insert(inst, sol, cache, r, u, p, k, cnt=None):
    r.seq = r.seq[:p] + [u] + r.seq[p:]
    if k != r.k and cnt is not None:
        cnt.type_changes += 1
    r.k = k
    r.m += inst.q[u]
    r.vol += inst.vol[u]
    r.L = route_len(inst, r.seq)
    r.cost = route_eval(inst, r.seq, k, cnt)
    cache.drop(r)


# ------------------------------------------------------------ M1: nearest neighbour

def nearest_neighbour(inst):
    un = set(range(1, inst.n + 1))
    routes = []
    d, a, b, s = inst.d, inst.a, inst.b, inst.s
    maxQ = max(inst.Q)
    while un:
        seq = []
        m = vol = 0.0
        t = [0.0] * inst.K           # current time per type
        alive = [True] * inst.K
        cur = 0
        while True:
            pick = None
            for u in inst.near[cur] if cur else sorted(un, key=lambda j: d[0][j]):
                if u not in un:
                    continue
                mm, vv = m + inst.q[u], vol + inst.vol[u]
                if mm > maxQ + 1e-9:
                    continue
                newt = []
                good = False
                for k in range(inst.K):
                    if not alive[k] or not cap_ok(inst, k, mm, vv):
                        newt.append(None)
                        continue
                    tu = max(a[u], t[k] + d[cur][u] / inst.v[k])
                    if tu <= b[u] + 1e-9 and tu + s[u] + d[u][0] / inst.v[k] <= inst.H + 1e-9:
                        newt.append(tu + s[u])
                        good = True
                    else:
                        newt.append(None)
                if good:
                    pick = (u, newt, mm, vv)
                    break
            if pick is None:
                break
            u, newt, m, vol = pick
            seq.append(u)
            for k in range(inst.K):
                if newt[k] is None:
                    alive[k] = False
                else:
                    t[k] = newt[k]
            un.discard(u)
            cur = u
        c, k = best_type(inst, seq, m, vol, route_len(inst, seq), None, False)
        routes.append(Route(inst, seq, k, c))
    return Sol(routes)


# ------------------------------------------------------------ M2: savings

def savings(inst):
    n = inst.n
    d = inst.d
    route_of = {}
    routes = {}
    for u in range(1, n + 1):
        c, k = new_route_option(inst, u)
        r = Route(inst, [u], k, c)
        routes[u] = r
        route_of[u] = u
    sv = []
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if i != j:
                sv.append((d[i][0] + d[0][j] - d[i][j], i, j))
    sv.sort(reverse=True)
    maxQ = max(inst.Q)
    for val, i, j in sv:
        if val <= 0:
            break
        ri, rj = route_of[i], route_of[j]
        if ri == rj:
            continue
        A, B = routes[ri], routes[rj]
        if A.seq[-1] != i or B.seq[0] != j:
            continue
        m, vol = A.m + B.m, A.vol + B.vol
        if m > maxQ + 1e-9:
            continue
        seq = A.seq + B.seq
        c, k = best_type(inst, seq, m, vol, route_len(inst, seq), None, False)
        if c == INF:
            continue
        nr = Route(inst, seq, k, c)
        routes[ri] = nr
        del routes[rj]
        for u in B.seq:
            route_of[u] = ri
    return Sol(list(routes.values()))


# ------------------------------------------------------------ M3: insertion with type choice

def insertion(inst, rng=None, rcl=1):
    """Sequential insertion: a route is seeded with the farthest unrouted customer, then the
    customer with the smallest cost increase (type change allowed) is inserted; with rcl > 1
    the customer is drawn at random among the rcl best candidates (used by M5)."""
    un = set(range(1, inst.n + 1))
    sol = Sol([])
    cache = RouteCache(inst)
    d = inst.d
    while un:
        far = [u for u in un]
        if rng is not None and rcl > 1:
            far.sort(key=lambda u: -d[0][u])
            seed = far[rng.randrange(min(rcl, len(far)))]
        else:
            seed = max(far, key=lambda u: (d[0][u], -u))
        c, k = new_route_option(inst, seed)
        r = Route(inst, [seed], k, c)
        sol.routes.append(r)
        un.discard(seed)
        while un:
            opts = []
            for u in un:
                delta, p, kk = insertion_options(inst, cache, r, u, True)
                if p >= 0:
                    opts.append((delta, u, p, kk))
            if not opts:
                break
            if rng is not None and rcl > 1:
                opts.sort()
                delta, u, p, kk = opts[rng.randrange(min(rcl, len(opts)))]
            else:
                delta, u, p, kk = min(opts)
            apply_insert(inst, sol, cache, r, u, p, kk)
            un.discard(u)
    return sol


def reinsert(inst, sol, custs, rng, noise=0.2, cnt=None):
    """Greedy reinsertion of removed customers (best position over all routes, type change
    allowed, multiplicative noise on the insertion cost); a new route is opened if needed."""
    cache = RouteCache(inst)
    for u in custs:
        best = (INF, None, -1, -1)
        for r in sol.routes:
            delta, p, k = insertion_options(inst, cache, r, u, True)
            if p >= 0:
                if noise:
                    delta = delta * (1.0 + rng.uniform(-noise, noise)) if delta > 0 else delta * (1.0 - rng.uniform(-noise, noise))
                if delta < best[0]:
                    best = (delta, r, p, k)
        c1, k1 = new_route_option(inst, u)
        if noise:
            c1 *= 1.0 + rng.uniform(-noise, noise)
        if best[1] is None or c1 < best[0]:
            c, k = new_route_option(inst, u)
            sol.routes.append(Route(inst, [u], k, c))
        else:
            _, r, p, k = best
            apply_insert(inst, sol, cache, r, u, p, k, cnt)
    return sol
