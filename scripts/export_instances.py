"""Write the 18 own test instances of papers [7] and [8] to data/own/ as JSON and text.

usage: python3 scripts/export_instances.py [outdir]   (default: data/own)
The instances are generated deterministically; the files are identical on every run.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import json

from hfvrptw.instance import generate, own_set


def to_txt(inst):
    lines = ["NAME : %s" % inst.name,
             "OBJECTIVE : fixed cost + cost per distance unit x route length",
             "CUSTOMERS : %d" % inst.n,
             "HORIZON : %g" % inst.H,
             "FLEET : unlimited number of vehicles of every type",
             "VEHICLE_TYPES_SECTION",
             "# id name mass_cap volume_cap fixed_cost cost_per_dist speed"]
    for k, t in enumerate(inst.types):
        lines.append("%d %s %g %g %g %g %g" % (k + 1, t["name"], t["Q"], t["W"], t["F"], t["c"], t["v"]))
    lines.append("NODE_SECTION")
    lines.append("# id x y mass volume ready due service   (node 0 = depot)")
    for i in range(inst.n + 1):
        lines.append("%d %.4f %.4f %g %g %g %g %g" % (i, inst.xy[i][0], inst.xy[i][1], inst.q[i],
                                                      inst.vol[i], inst.a[i], inst.b[i], inst.s[i]))
    lines.append("EOF")
    return "\n".join(lines) + "\n"


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "own")
    d = out
    os.makedirs(d, exist_ok=True)
    for spec in own_set():
        inst = generate(*spec)
        with open(os.path.join(d, inst.name + ".json"), "w") as f:
            json.dump(inst.to_json(), f, indent=1)
        with open(os.path.join(d, inst.name + ".txt"), "w") as f:
            f.write(to_txt(inst))
    print("wrote %d instances to %s" % (len(own_set()), d))


if __name__ == "__main__":
    main()
