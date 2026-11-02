"""Independent feasibility checker. It recomputes everything from the raw instance
fields (coordinates, demands, windows, type parameters) and does not use any code
of the search methods."""
import math


def check(inst, routes, claimed=None, tol=1e-6):
    """routes: list of [type index, [customers]]. Returns (ok, violations, cost)."""
    viol = []
    seen = {}
    total = 0.0
    xy = inst.xy
    for ri, (k, seq) in enumerate(routes):
        if not seq:
            continue
        tp = inst.types[k]
        speed = tp.get("v", 1.0)
        mass = sum(inst.q[i] for i in seq)
        volume = sum(inst.vol[i] for i in seq)
        if mass > tp["Q"] + tol:
            viol.append("route %d: mass %.2f > %.2f" % (ri, mass, tp["Q"]))
        W = tp.get("W", float("inf"))
        if volume > W + tol:
            viol.append("route %d: volume %.2f > %.2f" % (ri, volume, W))
        # schedule with departure at time 0
        dist, prev, t, service = 0.0, 0, 0.0, 0.0
        waits, starts = [], []
        for i in seq:
            if i in seen:
                viol.append("customer %d served twice" % i)
            seen[i] = ri
            leg = math.dist(xy[prev], xy[i])
            dist += leg
            arrive = t + leg / speed
            t = max(arrive, inst.a[i])
            waits.append(t - arrive)
            starts.append(t)
            if t > inst.b[i] + tol:
                viol.append("route %d: customer %d late (%.2f > %.2f)" % (ri, i, t, inst.b[i]))
            t += inst.s[i]
            service += inst.s[i]
            prev = i
        leg = math.dist(xy[prev], xy[0])
        dist += leg
        t += leg / speed
        if t > inst.H + tol:
            viol.append("route %d: returns at %.2f > horizon %.2f" % (ri, t, inst.H))
        if inst.objective == "enroute":
            # latest feasible departure: delaying by x shifts customer i by max(0, x - waiting before
            # and at i); the largest x keeping every window is min_i(cum_wait_i + b_i - start_i)
            cum, best_x = 0.0, float("inf")
            for idx, i in enumerate(seq):
                cum += waits[idx]
                best_x = min(best_x, cum + inst.b[i] - starts[idx])
            x = max(0.0, min(sum(waits), best_x))
            total += tp["F"] + (t - x - service)
        else:
            total += tp["F"] + tp.get("c", 1.0) * dist
    missing = [i for i in range(1, inst.n + 1) if i not in seen]
    if missing:
        viol.append("%d customers not served" % len(missing))
    if claimed is not None and abs(claimed - total) > 1e-4 * max(1.0, abs(total)):
        viol.append("claimed cost %.4f != recomputed %.4f" % (claimed, total))
    return not viol, viol, total
