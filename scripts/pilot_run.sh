#!/bin/bash
# Run one unattended single-machine experiment and collect its outputs.
#
# Usage: scripts/pilot_run.sh <config.yaml> <start-protocol> <duration-seconds> <out-dir> [learning]
# Example: scripts/pilot_run.sh exp/pilot/smoke-fixed-noattack.yaml pbft 120 results/smoke-pbft
#
# The given config temporarily replaces config/config.framework.yaml (restored afterwards).

set -u
if [ $# -lt 4 ]; then
  sed -n 2,7p "$0"; exit 1
fi

ROOT="$HOME/BFTBrain"
config=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
protocol=$2
duration=$3
out=$4
learning=${5:-}

mkdir -p "$out"
out=$(cd "$out" && pwd)

cd "$ROOT"
cp config/config.framework.yaml "$out/.framework.backup.yaml"
cp "$config" config/config.framework.yaml
cp "$config" "$out/config.yaml"

restore() {
  cp "$out/.framework.backup.yaml" "$ROOT/config/config.framework.yaml"
  rm -f "$out/.framework.backup.yaml"
}
trap restore EXIT

# Fresh output folders for this run
mkdir -p code/benchmarks code/logs
rm -rf code/benchmarks/* code/logs/*   # keeps the tracked .gitkeep files

cd scripts
DURATION="$duration" bash ./local_exp.sh "$protocol" $learning > "$out/driver.txt" 2>&1
sleep 5

# Save each tmux window's recent output (server, replicas, client, learning agents)
for s in cloudlab cloudlab-learning; do
  if tmux has-session -t "$s" 2>/dev/null; then
    for w in $(tmux list-windows -t "$s" -F '#I'); do
      tmux capture-pane -p -S -3000 -t "$s:$w" > "$out/pane-$s-$w.txt"
    done
    tmux kill-session -t "$s"
  fi
done

# Make sure no Java process is left on the experiment ports
for p in 9020 9021 9022 9023 9024 9025; do
  pids=$(lsof -t -i :"$p" 2>/dev/null)
  [ -n "$pids" ] && kill -9 $pids 2>/dev/null
done

cd "$ROOT/code"
mkdir -p "$out/benchmarks" "$out/logs" "$out/agent-data"
cp benchmarks/* "$out/benchmarks/" 2>/dev/null
cp logs/* "$out/logs/" 2>/dev/null
# learning agents' per-epoch state/reward CSVs written during this run
find learning/data -name '*.csv' -newer "$out/config.yaml" -exec cp {} "$out/agent-data/" \; 2>/dev/null

echo "Throughput samples (req/s):"
grep -h "^throughput" "$out"/benchmarks/*.txt 2>/dev/null | awk '{print $2}' | tr '\n' ' '; echo

echo "Episode reports:"
grep -h "EPISODE REPORT" "$out"/pane-*.txt "$out"/logs/*.log 2>/dev/null | sort -u | head -50
echo "Saved to $out"
