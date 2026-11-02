"""Instances of the heterogeneous fleet VRP with time windows (HFVRPTW).

Two families are supported:

* own instances (papers [7] and [8]): generated with fixed seeds, three vehicle
  types (truck, van, cargo bike) that differ in payload, cargo volume, fixed cost,
  cost per distance unit and speed; objective = fixed costs + variable costs;
* Liu & Shen (1999) fleet size and mix VRPTW: Solomon's 56 instances with 100
  customers and class-dependent vehicle types; objective (FT) = fixed costs +
  en-route time (travel + waiting, service excluded).
"""
import json
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

# Vehicle types of papers [7] and [8], table 1
OWN_TYPES = [
    dict(name="truck", Q=200.0, W=60.0, F=180.0, c=1.40, v=0.85),
    dict(name="van", Q=100.0, W=32.0, F=100.0, c=1.00, v=1.00),
    dict(name="bike", Q=30.0, W=9.0, F=35.0, c=0.45, v=0.70),
]


class Instance:
    """Node 0 is the depot. objective: 'cost' (F + c*L) or 'enroute' (F + travel + waiting)."""

    def __init__(self, name, xy, q, vol, a, b, s, types, H, objective="cost"):
        self.name = name
        self.xy = [tuple(p) for p in xy]
        self.q = list(q)
        self.vol = list(vol)
        self.a = list(a)
        self.b = list(b)
        self.s = list(s)
        self.types = [dict(t) for t in types]
        self.H = float(H)
        self.objective = objective
        self.n = len(xy) - 1
        self.K = len(types)
        N = len(xy)
        self.d = [[math.hypot(xy[i][0] - xy[j][0], xy[i][1] - xy[j][1]) for j in range(N)]
                  for i in range(N)]
        # neighbour lists (by distance), used by the constructive methods
        self.near = [sorted(range(1, N), key=lambda j: self.d[i][j]) for i in range(N)]
        for i in range(N):
            if i in self.near[i]:
                self.near[i].remove(i)
        self.Q = [t["Q"] for t in types]
        self.W = [t.get("W", float("inf")) for t in types]
        self.F = [t["F"] for t in types]
        self.c = [t.get("c", 1.0) for t in types]
        self.v = [t.get("v", 1.0) for t in types]

    def to_json(self):
        return dict(
            name=self.name, objective=self.objective, horizon=self.H,
            vehicle_types=[dict(name=t["name"], mass_cap=t["Q"],
                                volume_cap=(None if t.get("W", float("inf")) == float("inf") else t["W"]),
                                fixed_cost=t["F"], cost_per_dist=t.get("c", 1.0),
                                speed=t.get("v", 1.0)) for t in self.types],
            nodes=[dict(id=i, x=self.xy[i][0], y=self.xy[i][1], mass=self.q[i],
                        volume=self.vol[i], ready=self.a[i], due=self.b[i], service=self.s[i])
                   for i in range(self.n + 1)])


def from_json(path):
    with open(path) as f:
        d = json.load(f)
    nodes = sorted(d["nodes"], key=lambda r: r["id"])
    types = [dict(name=t["name"], Q=t["mass_cap"],
                  W=(float("inf") if t["volume_cap"] is None else t["volume_cap"]),
                  F=t["fixed_cost"], c=t["cost_per_dist"], v=t["speed"]) for t in d["vehicle_types"]]
    return Instance(d["name"], [(r["x"], r["y"]) for r in nodes], [r["mass"] for r in nodes],
                    [r["volume"] for r in nodes], [r["ready"] for r in nodes],
                    [r["due"] for r in nodes], [r["service"] for r in nodes], types,
                    d["horizon"], d.get("objective", "cost"))


# ---------------------------------------------------------------- own generator

def generate(cls, n, idx):
    """Own instance (papers [7], [8]): coordinates in [0,100]^2, depot in the centre;
    class R uniform, C clustered (5 clusters up to 50 customers, 8 above), RC half and half;
    72 % small orders (2..9 mass units), the rest large (18..45); volume = mass x density
    from {0.15, 0.25, 0.35, 0.50}; service time 10; time windows of width 120 (60 for C)
    placed around a nearest-neighbour reference tour scaled to 80 % of the horizon 720
    and kept reachable by the slowest vehicle type."""
    seed = {"R": 1, "C": 2, "RC": 3}[cls] * 100000 + n * 10 + idx
    rng = random.Random(seed)
    depot = (50.0, 50.0)
    pts = []
    centers = []
    if cls in ("C", "RC"):
        nc = 5 if n <= 50 else 8
        centers = [(rng.uniform(10, 90), rng.uniform(10, 90)) for _ in range(nc)]
    ncl = n if cls == "C" else (n // 2 if cls == "RC" else 0)
    for i in range(n):
        if i < ncl:
            cx, cy = centers[rng.randrange(len(centers))]
            pts.append((min(100.0, max(0.0, rng.gauss(cx, 5.0))), min(100.0, max(0.0, rng.gauss(cy, 5.0)))))
        else:
            pts.append((rng.uniform(0, 100), rng.uniform(0, 100)))
    xy = [depot] + pts
    q, vol = [0.0], [0.0]
    dens = [0.15, 0.25, 0.35, 0.50]
    for i in range(n):
        m = float(rng.randint(2, 9)) if rng.random() < 0.72 else float(rng.randint(18, 45))
        q.append(m)
        vol.append(round(m * dens[rng.randrange(4)], 2))
    s = [0.0] + [10.0] * n
    H = 720.0
    width = 60.0 if cls == "C" else 120.0
    vmin = min(t["v"] for t in OWN_TYPES)
    unv = set(range(1, n + 1))
    cur, t = 0, 0.0
    arr = [0.0] * (n + 1)
    while unv:
        nxt = min(unv, key=lambda j: (math.hypot(xy[cur][0] - xy[j][0], xy[cur][1] - xy[j][1]), j))
        t += math.hypot(xy[cur][0] - xy[nxt][0], xy[cur][1] - xy[nxt][1]) + 10.0
        arr[nxt] = t
        unv.discard(nxt)
        cur = nxt
    scale = (H * 0.8) / t
    a, b = [0.0], [H]
    for i in range(1, n + 1):
        d0 = math.hypot(xy[i][0] - 50.0, xy[i][1] - 50.0)
        centre = arr[i] * scale + rng.uniform(-60, 60)
        lo = max(d0 / vmin + 1.0, centre - width / 2.0)
        hi = lo + width
        latest = H - 10.0 - d0 / vmin - 1.0
        if hi > latest:
            hi = latest
            lo = max(d0 / vmin + 1.0, hi - width)
        a.append(round(lo, 1))
        b.append(round(hi, 1))
    return Instance("%s%d_%d" % (cls, n, idx), xy, q, vol, a, b, s, OWN_TYPES, H, "cost")


def own_set():
    return [(c, n, i) for n in (25, 50, 100) for c in ("R", "C", "RC") for i in (0, 1)]


# ---------------------------------------------------------------- Solomon / Liu-Shen

SOLOMON = os.path.join(DATA, "solomon")


def _parse_vrplib(path):
    sec, meta = None, {}
    coords, dem, tw = {}, {}, {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line == "EOF":
                continue
            if line.endswith("SECTION"):
                sec = line
                continue
            if ":" in line and sec is None:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
                continue
            p = line.split()
            if sec == "NODE_COORD_SECTION":
                coords[int(p[0])] = (float(p[1]), float(p[2]))
            elif sec == "DEMAND_SECTION":
                dem[int(p[0])] = float(p[1])
            elif sec == "TIME_WINDOW_SECTION":
                tw[int(p[0])] = (float(p[1]), float(p[2]))
    ids = sorted(coords)
    xy = [coords[i] for i in ids]
    q = [dem[i] for i in ids]
    a = [tw[i][0] for i in ids]
    b = [tw[i][1] for i in ids]
    st = float(meta.get("SERVICE_TIME", 0))
    s = [0.0] + [st] * (len(ids) - 1)
    return meta, xy, q, a, b, s


def solomon_names():
    return sorted(f[:-4] for f in os.listdir(SOLOMON) if f.endswith(".vrp"))


def solomon_class(name):
    for p in ("RC", "R", "C"):
        if name.startswith(p):
            return p + name[len(p)]
    raise ValueError(name)


def liu_shen(name, structure="A"):
    """Liu & Shen (1999) FSMVRPTW instance: Solomon customers, class vehicle types,
    unlimited fleet, objective FT (fixed cost + en-route time)."""
    meta, xy, q, a, b, s = _parse_vrplib(os.path.join(SOLOMON, name + ".vrp"))
    with open(os.path.join(DATA, "liu_shen", "types.json")) as f:
        tab = json.load(f)[solomon_class(name)]
    types = [dict(name=t["name"], Q=float(t["capacity"]), W=float("inf"),
                  F=float(t["fixed_cost_" + structure]), c=1.0, v=1.0) for t in tab]
    vol = [0.0] * len(xy)
    return Instance("%s%s" % (name, structure), xy, q, vol, a, b, s, types, b[0], "enroute")


def liu_shen_bks(structure="A"):
    import csv
    out = {}
    with open(os.path.join(DATA, "liu_shen", "bks.csv")) as f:
        for r in csv.DictReader(f):
            if r["cost_structure"] == structure:
                out[r["instance"]] = float(r["bks"])
    return out


def solomon_vrptw(name):
    """Classical VRPTW special case: one vehicle type, distance objective
    (used only as a sanity check of the implementation)."""
    meta, xy, q, a, b, s = _parse_vrplib(os.path.join(SOLOMON, name + ".vrp"))
    types = [dict(name="vehicle", Q=float(meta["CAPACITY"]), W=float("inf"), F=0.0, c=1.0, v=1.0)]
    return Instance(name, xy, q, [0.0] * len(xy), a, b, s, types, b[0], "cost")


def solomon_bks(name):
    with open(os.path.join(SOLOMON, name + ".sol")) as f:
        for line in f:
            if line.startswith("Cost"):
                return float(line.split()[1])
