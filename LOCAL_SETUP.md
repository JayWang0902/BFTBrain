# Running BFTBrain on one machine (our project setup)

Everything for our project lives on the `attack-pilot` branch. The original README covers CloudLab; this file covers a single laptop.

## Where things are

| Path | What |
| --- | --- |
| `paper/draft.md` | Paper draft, written as we go |
| `reports/` | Progress reports (snapshots) |
| `exp/pilot/` | Configs for our experiments |
| `results/<run>/` | Outputs of each run: config, logs, benchmarks, learning-agent CSVs |
| `scripts/pilot_run.sh` | Runs one unattended experiment and collects outputs |
| `scripts/analyze_pilot.py` | Per-minute protocol share and throughput for a run |

## One-time setup (macOS)

1. Clone to `~/BFTBrain` (scripts assume this path) and check out `attack-pilot`.
2. Tools: `brew install maven tmux`, and a JDK 20 (the code needs exactly 20, e.g. Temurin 20.0.2) unpacked under `~/bft-tools/`.
3. Python env for the learning agents:

```bash
cd ~/BFTBrain && python3 -m venv .venv && .venv/bin/pip install numpy pandas scikit-learn matplotlib tqdm grpcio "protobuf>=4.21,<5" pexpect xmltodict
```

4. `cp scripts/local_env.example.sh scripts/local_env.sh` and fix the JDK path inside.
5. Build:

```bash
cd ~/BFTBrain/code && source ../scripts/local_env.sh && mvn -q -B $MAVEN_OPTS compile dependency:copy-dependencies
```

## Running an experiment

```bash
cd ~/BFTBrain && scripts/pilot_run.sh exp/pilot/pilot2-20ms.yaml pbft 800 results/my-run learning
```

Arguments: config, starting protocol, duration in seconds, output folder, and `learning` to enable protocol switching (omit for a fixed protocol). Keep the machine awake while it runs. Then:

```bash
cd ~/BFTBrain && .venv/bin/python scripts/analyze_pilot.py results/my-run 60
```
