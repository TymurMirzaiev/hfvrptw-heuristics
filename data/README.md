# Data

Three sets of test instances. All solutions in `../results/` refer to these files.

| Folder | What | Instances | Used in |
|---|---|---|---|
| [`own/`](own/) | our generated instances with three vehicle types (truck, van, cargo bike) of different speeds | 18 | main test of papers [7] and [8] |
| [`liu_shen/`](liu_shen/) | vehicle types and best-known solutions of the Liu & Shen (1999) benchmark, built on Solomon's customers | 56 (cost structure A) | [7]: comparison with best-known solutions (all 56); [8]: check with 3–6 types (12) |
| [`solomon/`](solomon/) | Solomon's VRPTW instances with best-known solutions (VRPLIB format, PyVRP collection, MIT licence) | 56 | [7]: code check (single vehicle type); customer data of Liu & Shen |

---

## `own/` — our 18 instances

**Names:** `R25_0` = class R, 25 customers, instance 0. Classes:
- **R**: customers spread uniformly;
- **C**: clustered;
- **RC**: half clustered, half uniform.

Each class has 25, 50 and 100 customers, with 2 instances per size: 3 × 3 × 2 = 18.

Every instance comes in two files with the same content:
- `.json`: full precision; load with `hfvrptw.instance.from_json(path)`.
- `.txt`: human-readable, shown below.

```
NAME : R25_0
...
VEHICLE_TYPES_SECTION
# id name mass_cap volume_cap fixed_cost cost_per_dist speed
1 truck 200 60 180 1.4 0.85
2 van 100 32 100 1 1
3 bike 30 9 35 0.45 0.7
NODE_SECTION
# id x y mass volume ready due service   (node 0 = depot)
0 50.0000 50.0000 0 0 0 720 0
1 ...
EOF
```

### Model rules

- **Fleet:** three types, as many vehicles of each type as needed, one trip per vehicle.
- **Distance:** Euclidean, not rounded.
- **Travel time:** distance / speed of the vehicle type.
- **Service time:** `service` of the node, the same for every type.
- **A route is feasible if:**
  - its total mass and volume fit the vehicle type;
  - service at every customer starts within `[ready, due]` (an early vehicle waits);
  - the vehicle returns to the depot by the horizon (720).
- **Every customer** is served exactly once.
- **Cost (minimised):** Σ over routes of (fixed cost + cost per distance × route length).

The vehicle type therefore changes both the cost **and** the speed of a route, so it also decides whether the time windows can be met.

### How the instances were generated

The instances are deterministic, with fixed seeds: `hfvrptw.instance.generate(cls, n, idx)`. Running `python3 scripts/export_instances.py` rewrites this folder with identical files.

- **Area:** depot at (50, 50) in a 100 × 100 square.
- **Customer locations:**
  - R: uniform;
  - C: 5 clusters (8 for 100 customers), Gaussian spread 5;
  - RC: half clustered, half uniform.
- **Orders:** 72 % weigh 2–9 units, the rest 18–45. Volume = weight × a density from {0.15, 0.25, 0.35, 0.50}.
- **Time windows:** width 120 (60 for class C), placed around a reference tour scaled to 80 % of the horizon, and always reachable by the slowest vehicle type.

---

## `liu_shen/` — public benchmark with known best solutions

The instances are not stored as separate files. They are built on the fly from Solomon's customers and the vehicle tables:

```python
from hfvrptw.instance import liu_shen, liu_shen_bks
inst = liu_shen("R101", "A")      # Solomon R101 customers + R1 vehicle types, cost structure A
bks = liu_shen_bks("A")           # {"R101": 4536.40, ...}
```

**Objective (as in Liu & Shen):** fixed cost + en-route time, i.e. travel time plus waiting time, without service time. The departure from the depot is delayed as much as possible, so waiting at the first customers is not counted unnecessarily.

The sources of every number are in [`liu_shen/SOURCES.md`](liu_shen/SOURCES.md).

## `solomon/` — Solomon VRPTW

`C101.vrp` … `RC208.vrp` (instances) and `.sol` (best-known solutions), from the PyVRP instance collection; licence in `LICENSE_PyVRP_Instances.txt`. They are used directly for the single-type sanity check (`solomon_vrptw(name)`), and as the customer data for Liu & Shen.
