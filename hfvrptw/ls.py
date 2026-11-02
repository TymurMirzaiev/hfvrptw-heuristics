"""Local search (variable neighbourhood descent) with a pluggable strategy for the
vehicle type change operator (paper [8]).

Neighbourhoods: inter-route relocate, inter-route swap, tail exchange (2-opt*),
intra-route reversal (2-opt). First improvement; a pass scans all four.

Strategies (when the type of a changed route is enumerated during move evaluation):
  C0  never (the type stays as built)
  C1  always (full enumeration at every move evaluation)
  C2  never during moves; every 3 passes all routes of the current solution are re-typed
  C3  only for routes whose payload or volume utilisation is below 0.65
  C4  with probability 0.2
  C5  with probability 0.5
  M4  never during moves; after every accepted move the changed routes try a cheaper type
      (local search of method M4 in paper [7])
"""
from .core import INF, Route, best_type, cap_ok, lower_bound, route_eval

EPS = 1e-7
UTIL = 0.65
GRAN = 20      # granular neighbourhood size
PROB = {"C4": 0.2, "C5": 0.5}


class LS:
    def __init__(self, inst, strategy, rng, cnt, clock=None, bound=True):
        self.inst = inst
        # bound=True: a move is evaluated only if the O(1) cost lower bound of the new routes
        # promises an improvement, and types are evaluated in increasing order of their bound;
        # bound=False ("naive"): every candidate move is evaluated in full for every admissible type
        self.bound = bound
        self.st = strategy
        self.rng = rng
        self.cnt = cnt
        self.clock = clock
        self.passes = 0
        self.near = [lst[:GRAN] for lst in inst.near]

    # ---- type options for a new route derived from original route r
    def enumerate_for(self, r):
        st = self.st
        if st == "C1":
            return True
        if st == "C3":
            inst = self.inst
            k = r.k
            u = max(r.m / inst.Q[k], (r.vol / inst.W[k]) if inst.W[k] != INF else 0.0)
            return u < UTIL
        if st in PROB:
            return self.rng.random() < PROB[st]
        return False

    def options(self, r, m, vol, L, enum):
        """Sorted (lower bound, k) of admissible types; None if the route would be empty."""
        inst = self.inst
        if enum:
            res = [(lower_bound(inst, k, L), k) for k in range(inst.K) if cap_ok(inst, k, m, vol)]
            res.sort()
            return res
        if cap_ok(inst, r.k, m, vol):
            return [(lower_bound(inst, r.k, L), r.k)]
        return []

    def realise(self, seq, opts, enum, limit):
        """Exact cost and type of seq among opts (only bound-promising types are evaluated)."""
        best, bk = INF, -1
        for lb, k in opts:
            if self.bound and (lb >= best - EPS or lb >= limit - EPS):
                break
            c = route_eval(self.inst, seq, k, self.cnt, enum)
            if c < best:
                best, bk = c, k
        return best, bk

    def screen(self, r1, m1, v1, L1, empty1, r2, m2, v2, L2, empty2):
        """Cheap bound test of a move (no route evaluation). Returns the type options or None."""
        old = r1.cost + (r2.cost if r2 is not None else 0.0)
        if empty1:
            e1, o1 = False, [(0.0, r1.k)]
        else:
            e1 = self.enumerate_for(r1)
            o1 = self.options(r1, m1, v1, L1, e1)
            if not o1:
                return None
        if r2 is None:
            e2, o2, lb2 = False, None, 0.0
        elif empty2:
            e2, o2, lb2 = False, [(0.0, r2.k)], 0.0
        else:
            e2 = self.enumerate_for(r2)
            o2 = self.options(r2, m2, v2, L2, e2)
            if not o2:
                return None
            lb2 = o2[0][0]
        if self.bound and o1[0][0] + lb2 >= old - EPS:
            return None
        if not self.bound:
            lb2 = 0.0
        return old, e1, o1, e2, o2, lb2

    def finish(self, scr, r1, s1, r2, s2):
        old, e1, o1, e2, o2, lb2 = scr
        if s1:
            c1, k1 = self.realise(s1, o1, e1, old - lb2)
            if c1 == INF:
                return None
        else:
            c1, k1 = 0.0, r1.k
        if r2 is not None:
            if s2:
                c2, k2 = self.realise(s2, o2, e2, old - c1)
                if c2 == INF:
                    return None
            else:
                c2, k2 = 0.0, r2.k
        else:
            c2, k2 = 0.0, -1
        gain = old - c1 - c2
        if gain > EPS:
            return gain, (c1, k1), (c2, k2)
        return None

    def commit(self, r, seq, m, vol, L, c, k):
        if k != r.k:
            self.cnt.type_changes += 1
        r.seq, r.m, r.vol, r.L, r.cost, r.k = seq, m, vol, L, c, k
        if self.st == "M4" and seq:
            c2, k2 = best_type(self.inst, seq, m, vol, L, self.cnt, True)
            if c2 < r.cost - EPS:
                self.cnt.type_changes += 1
                r.cost, r.k = c2, k2

    def timeout(self):
        return self.clock is not None and self.clock.out()

    # ---- neighbourhoods (granular: only arcs to one of the G nearest customers are created)
    def relocate(self, sol):
        inst = self.inst
        d, q, vol = inst.d, inst.q, inst.vol
        near = self.near
        R = sol.routes
        pos = {}
        for ri, r in enumerate(R):
            for p_, x in enumerate(r.seq):
                pos[x] = (ri, p_)
        u_list = [u for r in R for u in r.seq]
        self.rng.shuffle(u_list)
        for u in u_list:
            if self.timeout():
                return
            a, i = pos[u]
            r1 = R[a]
            pv = r1.seq[i - 1] if i > 0 else 0
            nx = r1.seq[i + 1] if i + 1 < len(r1.seq) else 0
            dl1 = d[pv][nx] - d[pv][u] - d[u][nx]
            empty1 = len(r1.seq) == 1
            L1 = 0.0 if empty1 else r1.L + dl1
            m1, v1 = r1.m - q[u], r1.vol - vol[u]
            done = False
            # candidate positions: before or after a near customer w in another route
            cands = set()
            for w in near[u]:
                b_, j = pos[w]
                if b_ != a:
                    cands.add((b_, j))
                    cands.add((b_, j + 1))
            for b_, p_ in sorted(cands):
                r2 = R[b_]
                seq2 = r2.seq
                prev = seq2[p_ - 1] if p_ > 0 else 0
                nxt = seq2[p_] if p_ < len(seq2) else 0
                dl2 = d[prev][u] + d[u][nxt] - d[prev][nxt]
                m2, v2 = r2.m + q[u], r2.vol + vol[u]
                scr = self.screen(r1, m1, v1, L1, empty1, r2, m2, v2, r2.L + dl2, False)
                if scr is None:
                    continue
                s1 = r1.seq[:i] + r1.seq[i + 1:]
                s2 = seq2[:p_] + [u] + seq2[p_:]
                res = self.finish(scr, r1, s1, r2, s2)
                if res:
                    g, (c1, k1), (c2, k2) = res
                    self.commit(r1, s1, m1, v1, L1, c1, k1)
                    self.commit(r2, s2, m2, v2, r2.L + dl2, c2, k2)
                    self.improved = True
                    for ri in (a, b_):
                        for p2, x in enumerate(R[ri].seq):
                            pos[x] = (ri, p2)
                    break
        sol.clean()

    def swap(self, sol):
        inst = self.inst
        d, q, vol = inst.d, inst.q, inst.vol
        near = self.near
        R = sol.routes
        pos = {}
        for ri, r in enumerate(R):
            for p_, x in enumerate(r.seq):
                pos[x] = (ri, p_)
        u_list = [u for r in R for u in r.seq]
        self.rng.shuffle(u_list)
        for u in u_list:
            if self.timeout():
                return
            for w in near[u]:
                a, i = pos[u]
                b_, j = pos[w]
                if a == b_:
                    continue
                r1, r2 = R[a], R[b_]
                pu = r1.seq[i - 1] if i > 0 else 0
                nu = r1.seq[i + 1] if i + 1 < len(r1.seq) else 0
                pw = r2.seq[j - 1] if j > 0 else 0
                nw = r2.seq[j + 1] if j + 1 < len(r2.seq) else 0
                dl1 = d[pu][w] + d[w][nu] - d[pu][u] - d[u][nu]
                dl2 = d[pw][u] + d[u][nw] - d[pw][w] - d[w][nw]
                m1, v1 = r1.m - q[u] + q[w], r1.vol - vol[u] + vol[w]
                m2, v2 = r2.m - q[w] + q[u], r2.vol - vol[w] + vol[u]
                scr = self.screen(r1, m1, v1, r1.L + dl1, False, r2, m2, v2, r2.L + dl2, False)
                if scr is None:
                    continue
                s1 = r1.seq[:i] + [w] + r1.seq[i + 1:]
                s2 = r2.seq[:j] + [u] + r2.seq[j + 1:]
                res = self.finish(scr, r1, s1, r2, s2)
                if res:
                    g, (c1, k1), (c2, k2) = res
                    self.commit(r1, s1, m1, v1, r1.L + dl1, c1, k1)
                    self.commit(r2, s2, m2, v2, r2.L + dl2, c2, k2)
                    pos[u], pos[w] = (b_, j), (a, i)
                    self.improved = True
                    break

    def two_opt_star(self, sol):
        """Tail exchange A[:i] + B[j:], B[:j] + A[i:], with the new arc (A[i-1], B[j]) restricted
        to near pairs."""
        inst = self.inst
        d, q, vol = inst.d, inst.q, inst.vol
        near = self.near
        R = sol.routes
        pos = {}
        for ri, r in enumerate(R):
            for p_, x in enumerate(r.seq):
                pos[x] = (ri, p_)
        u_list = [u for r in R for u in r.seq]
        self.rng.shuffle(u_list)
        for u in u_list:
            if self.timeout():
                return
            for w in near[u]:
                a, i0 = pos[u]
                b_, j = pos[w]
                if a == b_:
                    continue
                r1, r2 = R[a], R[b_]
                A, B = r1.seq, r2.seq
                i = i0 + 1          # A[:i] ends with u, B[j:] starts with w
                ai, an = u, (A[i] if i < len(A) else 0)
                bj, bn = (B[j - 1] if j > 0 else 0), w
                hA = sum(q[x] for x in A[:i]); hvA = sum(vol[x] for x in A[:i])
                hB = sum(q[x] for x in B[:j]); hvB = sum(vol[x] for x in B[:j])
                m1, v1 = hA + (r2.m - hB), hvA + (r2.vol - hvB)
                m2, v2 = hB + (r1.m - hA), hvB + (r1.vol - hvA)
                plA = self._prefix_len(A, i)
                plB = self._prefix_len(B, j)
                s1_empty = False
                s2_empty = (j == 0 and i == len(A))
                L1 = plA + d[ai][bn] + (r2.L - plB - d[bj][bn])
                L2 = 0.0 if s2_empty else plB + d[bj][an] + (r1.L - plA - d[ai][an])
                scr = self.screen(r1, m1, v1, L1, s1_empty, r2, m2, v2, L2, s2_empty)
                if scr is None:
                    continue
                s1 = A[:i] + B[j:]
                s2 = B[:j] + A[i:]
                res = self.finish(scr, r1, s1, r2, s2)
                if res:
                    g, (c1, k1), (c2, k2) = res
                    self.commit(r1, s1, m1, v1, L1, c1, k1)
                    self.commit(r2, s2, m2, v2, L2, c2, k2)
                    self.improved = True
                    for ri in (a, b_):
                        for p2, x in enumerate(R[ri].seq):
                            pos[x] = (ri, p2)
                    break
        sol.clean()

    def _prefix_len(self, S, i):
        d = self.inst.d
        prev, L = 0, 0.0
        for x in S[:i]:
            L += d[prev][x]
            prev = x
        return L

    def two_opt(self, sol):
        d = self.inst.d
        for r in sol.routes:
            restart = True
            while restart:
                restart = False
                S = r.seq
                n = len(S)
                for i in range(n - 1):
                    a = S[i - 1] if i > 0 else 0
                    for j in range(i + 1, n):
                        b = S[j + 1] if j + 1 < n else 0
                        dl = d[a][S[j]] + d[S[i]][b] - d[a][S[i]] - d[S[j]][b]
                        scr = self.screen(r, r.m, r.vol, r.L + dl, False, None, 0, 0, 0, False)
                        if scr is None:
                            continue
                        s1 = S[:i] + S[i:j + 1][::-1] + S[j + 1:]
                        res = self.finish(scr, r, s1, None, None)
                        if res:
                            g, (c1, k1), _ = res
                            self.commit(r, s1, r.m, r.vol, r.L + dl, c1, k1)
                            self.improved = True
                            restart = True
                            break
                    if restart or self.timeout():
                        break
                if self.timeout():
                    return

    def retype_all(self, sol):
        for r in sol.routes:
            c, k = best_type(self.inst, r.seq, r.m, r.vol, r.L, self.cnt, True)
            if c < r.cost - EPS:
                self.cnt.type_changes += 1
                r.cost, r.k = c, k
                self.improved = True

    def run(self, sol, max_passes=None):
        while True:
            self.improved = False
            self.relocate(sol)
            if not self.timeout():
                self.swap(sol)
            if not self.timeout():
                self.two_opt_star(sol)
            if not self.timeout():
                self.two_opt(sol)
            self.passes += 1
            if self.st == "C2" and self.passes % 3 == 0 and not self.timeout():
                self.retype_all(sol)
            sol.clean()
            if not self.improved or self.timeout():
                if self.st == "C2" and self.passes % 3 != 0 and not self.timeout() and not self.improved:
                    # final re-typing at convergence, as the periodic pass would do
                    self.retype_all(sol)
                    sol.clean()
                    if self.improved:
                        continue
                break
            if max_passes and self.passes >= max_passes:
                break
        return sol
