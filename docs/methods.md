# Methods and code

For a gentler, illustrated walk-through, see [How it works](how-it-works.md).

## Code map (`hfvrptw/`)

| File | What it does |
|---|---|
| `instance.py` | `Instance` class; generator of our 18 instances (`generate`, `own_set`); readers for Solomon (`solomon_vrptw`) and Liu & Shen (`liu_shen`, `liu_shen_bks`); `from_json` |
| `core.py` | route evaluation: one pass over a route checks mass, volume and time windows and returns its cost. Also the cheapest feasible type of a route (`best_type`), the constant-time cost lower bound (`lower_bound`), the evaluation counter and the time budget clock |
| `construct.py` | constructive methods M1–M3. Also greedy reinsertion, used by iterated local search. Insertion checks time windows in constant time using earliest/latest start times precomputed for each route |
| `ls.py` | local search (`LS`) with the vehicle type change strategies C0–C5 and the M4 rule |
| `meta.py` | M4, M5 (multistart) and M6 (iterated local search) |
| `checker.py` | independent feasibility checker. It shares no code with the methods and recomputes loads, arrival times, windows and cost from the raw data |

## The six methods (paper [7])

| Code | Method | In short |
|---|---|---|
| M1 | Nearest neighbour | extend the route with the nearest customer that still fits; give the finished route its cheapest feasible type |
| M2 | Savings (Clarke & Wright) | start with one route per customer and merge routes in decreasing order of distance saving, if some vehicle type can serve the merged route |
| M3 | Insertion with type choice | start a route at the farthest unserved customer, then insert the customer with the smallest cost increase. The increase already includes switching to another type, so an insertion can pay off even if it needs a bigger vehicle |
| M4 | M3 + local search | descent over four neighbourhoods until no improvement: move a customer to another route, swap two customers, exchange route tails (2-opt\*), reverse a segment (2-opt). Granular: 20 nearest neighbours; first improvement |
| M5 | Multistart | repeat until the time budget is spent: randomised insertion (pick one of the 3 best candidates), then local search; keep the best |
| M6 | Iterated local search | remove 10–30 % random customers, reinsert them greedily with ±20 % noise, run local search. Improvements are always accepted; worse solutions within 2 % are accepted with probability 0.3 |

**The selection rule of paper [7]:**
1. Measure the time of one M4 descent on your instance.
2. If the time budget is below about 2× that time, use M4.
3. From about 2× upwards, use M6.
4. From 5× upwards, M6 was better than M4 on every instance.

## Vehicle type change strategies (paper [8])

The *type change operator* gives a route another vehicle type. Unlike ordinary moves, it changes the cost **and** the travel times of the whole route at once. The strategies differ in when local search tries other types for the routes changed by a move:

| Code | When types are tried during move evaluation |
|---|---|
| C0 | never: the type chosen at construction stays |
| C1 | always: all types, at every move evaluation |
| C2 | never during moves; every 3 passes all routes of the solution are re-typed |
| C3 | only for routes whose mass or volume utilisation is below 0.65 |
| C4 | with probability 0.2 |
| C5 | with probability 0.5 |
| M4 | never during moves; after every accepted move, changed routes try a cheaper type (the local search of M4) |

### The cost lower bound

For a route of length *L* on type *k*, *F<sub>k</sub>* + *c<sub>k</sub>* · *L* costs O(1) to compute:
- **Our instances:** it is the exact cost. What still needs a full pass over the route is checking the time windows at that type's speed.
- **Liu & Shen:** it is a lower bound (*F<sub>k</sub>* + *L*), since en-route time is at least the distance.

With `bound=True` (the default):
- a move is evaluated in full only if the bound for the new routes promises an improvement;
- types are tried in increasing order of their bound, stopping as soon as the next bound cannot beat the best type found.

With `bound=False` (the "naive" experiments) every candidate move is evaluated in full for every admissible type.

**The main finding of paper [8]:** with the bound, trying all types (C1) costs only 1.03× the route evaluations of never trying them (C0), instead of 1.63× without the bound, and it gives the best solutions.

## Using the code

```python
from hfvrptw.instance import from_json
from hfvrptw.meta import ils
from hfvrptw.checker import check

inst = from_json("data/own/RC100_0.json")
sol, info = ils(inst, budget=4.0, seed=1, strategy="C1")   # M6 with full type enumeration
routes = [(r.k, r.seq) for r in sol.routes]
print(sol.cost(), check(inst, routes))
```

Or from the command line: `python3 examples/solve.py data/own/RC100_0.json --method M6 --time 4 --out plan.json`.
