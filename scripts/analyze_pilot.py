"""Summarize one pilot run: which protocol was chosen over time, and throughput.

Usage: .venv/bin/python scripts/analyze_pilot.py results/pilot-1 [bucket-seconds]
Reads the [EPISODE REPORT] lines that replica 0 writes to its log.
"""
import glob
import re
import sys
from collections import Counter

run_dir = sys.argv[1]
bucket = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0

pattern = re.compile(
    r"episode (\d+): protocol = (\w+) , throughput = ([\d.]+)req/s , "
    r"episode time = ([\d.]+)s, overall time = ([\d.]+)s")

episodes = []
for path in glob.glob(f"{run_dir}/logs/*u0.log"):
    with open(path) as f:
        for line in f:
            m = pattern.search(line)
            if m:
                ep, proto, tput, dur, total = m.groups()
                episodes.append((int(ep), proto, float(tput), float(dur), float(total)))
episodes.sort()

if not episodes:
    sys.exit("no episode reports found")

print(f"{len(episodes)} episodes, {episodes[-1][4]:.0f} s of run time\n")
print(f"{'window (s)':>12} {'episodes':>8} {'avg tput':>10}  protocol share")
start = 0.0
while start < episodes[-1][4]:
    window = [e for e in episodes if start <= e[4] - e[3] < start + bucket]
    if window:
        # time-weighted throughput: requests done / time spent
        reqs = sum(e[2] * e[3] for e in window)
        secs = sum(e[3] for e in window)
        share = Counter()
        for e in window:
            share[e[1]] += e[3]
        mix = ", ".join(f"{p} {100 * t / secs:.0f}%" for p, t in share.most_common())
        print(f"{start:5.0f}-{start + bucket:<6.0f} {len(window):>8} {reqs / secs:>10.0f}  {mix}")
    start += bucket

switches = sum(1 for a, b in zip(episodes, episodes[1:]) if a[1] != b[1])
print(f"\nprotocol switches: {switches}")
