"""Compare Phase 2 runs (on/off attack): adaptive vs fixed protocols.

Usage: .venv/bin/python scripts/analyze_phase2.py results/phase2-adaptive results/phase2-fixed-zyzzyva results/phase2-fixed-prime

Throughput comes from the coordinator's benchmark samples (one every
benchmark-interval-ms, 3 s by default), so adaptive and fixed runs are measured
the same way. Attack phases follow the schedule in the configs (times from
replica start); benchmark samples start a few seconds later, so phase
boundaries are approximate (+/- one sample).
"""
import glob
import re
import sys

SAMPLE_S = 3.0
# (start, end, attack on?) in seconds, from exp/pilot/phase2-onoff-*.yaml
PHASES = [(0, 180, False), (180, 360, True), (360, 540, False), (540, 720, True), (720, 900, False)]
SKIP_S = 60  # first minute: start-up and BFTBrain's initial exploration


def samples(run_dir):
    vals = []
    for path in glob.glob(f"{run_dir}/benchmarks/*.txt"):
        with open(path) as f:
            vals += [float(m) for m in re.findall(r"^throughput\s+([\d.]+)req/s", f.read(), re.M)]
    return vals


def episodes(run_dir):
    pat = re.compile(r"episode (\d+): protocol = (\w+) , throughput = ([\d.]+)req/s , "
                     r"episode time = ([\d.]+)s, overall time = ([\d.]+)s")
    out = []
    for path in glob.glob(f"{run_dir}/logs/*u0.log"):
        with open(path) as f:
            out += [(int(a), b, float(c), float(d), float(e)) for a, b, c, d, e in pat.findall(f.read())]
    return sorted(out)


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


rows = []
for run in sys.argv[1:]:
    s = samples(run)
    t = [i * SAMPLE_S for i in range(len(s))]
    overall = mean([v for v, ti in zip(s, t) if ti >= SKIP_S])
    per_phase = []
    for a, b, on in PHASES:
        lo = max(a, SKIP_S)
        per_phase.append(mean([v for v, ti in zip(s, t) if lo <= ti < b]))
    rows.append((run.rstrip("/").split("/")[-1], overall, per_phase))

print(f"{'run':<24} {'avg (from 60 s)':>15} " + " ".join(
    f"{('ON ' if on else 'off') + f' {a}-{b}':>13}" for a, b, on in PHASES))
for name, overall, per_phase in rows:
    print(f"{name:<24} {overall:>15.0f} " + " ".join(f"{v:>13.0f}" for v in per_phase))

# Protocol timeline for adaptive runs
for run in sys.argv[1:]:
    eps = episodes(run)
    if not eps:
        continue
    print(f"\n{run}: {len(eps)} epochs, "
          f"{sum(1 for x, y in zip(eps, eps[1:]) if x[1] != y[1])} switches")
    for a, b, on in PHASES:
        win = [e for e in eps if a <= e[4] - e[3] < b]
        secs = sum(e[3] for e in win) or 1
        share = {}
        for e in win:
            share[e[1]] = share.get(e[1], 0) + e[3]
        mix = ", ".join(f"{p} {100 * v / secs:.0f}%" for p, v in sorted(share.items(), key=lambda kv: -kv[1]))
        print(f"  {'ON ' if on else 'off'} {a:>3}-{b:<3} s  {len(win):>4} epochs  {mix}")
    print("  sequence:", " ".join(f"{int(e[4])}:{e[1][:4]}" for e in eps
                                  if e[4] > 170 and (eps.index(e) == 0 or eps[eps.index(e) - 1][1] != e[1])))
