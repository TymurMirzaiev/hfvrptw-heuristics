# Liu & Shen (1999) benchmark: where the numbers come from

The Liu & Shen instances for the fleet size and mix VRP with time windows (FSMVRPTW) use the customers of Solomon's 56 instances with 100 customers (`../solomon/`). The vehicle capacity in the Solomon file is ignored; each Solomon class has its own set of vehicle types, with three cost structures A, B and C. This repository uses cost structure **A**.

| File | Contents |
|---|---|
| `types.json` | vehicle types per Solomon class: capacity and fixed cost for A, B and C |
| `bks.csv` | best-known solution per instance and cost structure, objective FT |
| `fd_class_averages.csv` | class averages for the other objective (FD), for comparison only |

## Vehicle types (`types.json`)

Two independent public transcriptions agree on every capacity and every fixed cost:

- J. Manguino, GitHub `jmanguino/FSMVRPTWSC`, `Instances/Literature Adapted/Vehicles.txt` (first column of the step-cost matrix).
- GitHub `rammohan2004/CVRP-with-Time-Windows-and-Varying-Vehicle-Capacities`, `instance-generator/solomon_to_fsmvrptw.py` (labelled as Liu & Shen's table; B = A/5, C = A/10).

Cross-check: for 156 of 168 solutions in Koç et al. (2015), the fixed cost implied by the published fleet mix and these types equals the published vehicle cost exactly. The 12 mismatches are listed under Caveats below and look like typos in the paper.

## Best-known solutions (`bks.csv`)

**Objective FT** (Liu & Shen's original): total fixed vehicle cost + total en-route time. En-route time is travel time plus waiting time, without service time; travel time equals Euclidean distance.

Source: Ç. Koç, T. Bektaş, O. Jabali, G. Laporte (2015). A hybrid evolutionary algorithm for heterogeneous fleet vehicle routing problems with time windows. *Computers & Operations Research* 64, 11–27, Appendix Tables A1–A3. The tables give the best of 10 runs of five methods:
- ReVNTS (2008);
- MDA (2008);
- AMP (2010);
- UHGS (2014);
- HEA (2015).

`bks` is the minimum of the five, and `best_method` names which method reached it. The values were cross-checked against the working paper CIRRELT-2014-16 and against the class averages in Table 2 of the paper.

These values date from 2015. Later papers may have improved some of them.

## Caveats

- The HEA values in CIRRELT-2014-16 differ from the published version for 19 instances. `bks.csv` uses the published values.
- **RC202B:** HEA is marked as a new best (2022.00), but ReVNTS reports 2002.62. `bks.csv` uses 2002.62.
- **C101C, C105C, C107C:** MDA reports values slightly below the common 1628.94. They are kept as the best-known values.
- **The MDA column** does not reproduce the MDA class averages in Table 2 of the paper. Use the per-instance MDA values with care.
- **Internal inconsistencies of HEA in the paper:**
  - fleet mix does not match the vehicle cost for R111A, RC107A, RC206A, RC207A, RC206B, R111C, RC108C, R204C, R209C, C205C, C207C and RC204C;
  - C203A and R211B: DC + VC ≠ TC.
- **Per-instance best-known values for FD were not available.** `fd_class_averages.csv` holds the class averages from Table 3 of Koç et al. (2015).
