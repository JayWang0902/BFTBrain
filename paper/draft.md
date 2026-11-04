# Adaptation Lag as an Attack Surface in Learning-Based BFT Protocol Selection

> Working draft. Written as we go; converted to LaTeX at the end.
> Notes for us are in `> [TODO]` / `> [NOTE]` blocks. Every number cites the run folder under `results/` it came from.

## Abstract (draft)

Adaptive Byzantine fault-tolerant (BFT) systems such as BFTBrain switch among consensus protocols at run time, using online learning to pick the protocol that performs best under the observed workload and faults. Their learning formulation assumes that the current protocol choice does not affect future fault patterns. We study what happens when a malicious replica violates this assumption. Using BFTBrain's own slow-proposal fault on a 4-replica deployment, we find that BFTBrain eventually converges to the right protocol under attack, but only after a long re-adaptation period (about 10 minutes in our setup) during which throughput is roughly one fifth of what the best protocol achieves. We trace this lag to three mechanisms: forced exploration of untried protocol transitions, an attack that becomes invisible to the learner under the immune protocol, and epochs that stretch when the system is slow. An attacker that repeatedly toggles its behavior can keep the system in this lag. We then propose [TODO: defenses, Phase 3] and show that [TODO: results].

## 1 Introduction

No single BFT protocol is best under all conditions: protocols with a fast path excel when all replicas respond, while protocols that bound the leader's influence hold up when the leader is slow or malicious. Adaptive systems exploit this by switching protocols at run time. BFTBrain [1] frames the choice as a contextual multi-armed bandit: at the end of each epoch, replicas agree on measured features (workload and fault indicators) and a learned model picks the protocol with the highest predicted throughput for the next epoch.

The bandit formulation rests on an explicit assumption. In the authors' words, "the current choice of protocol does not affect the pattern of workloads and faults in future epochs" [1]. A Byzantine replica is not bound by this assumption: it knows which protocol is running and can change its behavior accordingly.

This paper asks whether the adaptation mechanism itself becomes an attack surface. Our findings so far:

- Under a slow-leader attack, the best protocol changes (from Zyzzyva to Prime), so adaptation is genuinely needed.
- BFTBrain does find the right protocol, but slowly, and the slowness has identifiable causes in its design.
- [TODO: Phase 2] Whether an on/off attacker makes adaptive selection worse than a fixed protocol.
- [TODO: Phase 3] Defenses that shorten the lag without hurting normal-case performance.

> [NOTE] Contribution framing agreed with the professor: (1) validation, (2) attack evaluation, (3) improvement; (3) is the main contribution.

## 2 Background: how BFTBrain selects a protocol

BFTBrain runs one of six protocols at a time: PBFT, Zyzzyva, CheapBFT, SBFT, HotStuff and Prime. Execution is divided into epochs of a fixed number of sequence numbers (1,000 in our configuration). At the end of each epoch:

1. **Measure.** Each replica reports features: request size, fast-path frequency, messages received per slot, and proposal slowness (the average interval between consecutive proposals), plus protocol properties (fast path, leader rotation).
2. **Agree.** Learning agents exchange reports through a validated consensus step and take the median of each field, so up to f lying agents cannot move a value outside the honest range.
3. **Predict.** For the current protocol `p`, a separate random-forest model for each transition `(p → q)` predicts the throughput of switching to `q` given the current features. Each model is trained on a bootstrap resample of its history, which gives Thompson-sampling-style exploration.
4. **Choose.** The protocol with the highest prediction runs the next epoch. A transition with no data yet is predicted as +∞, so every untried transition is tried once before the model is trusted.

Two details matter for this paper. First, the reward observed for an epoch is its throughput, so an attacked epoch both records a low reward and takes longer to complete. Second, BFTBrain's implementation of Prime disables the slow-proposal fault (`fault-override` in `config/config.prime.yaml`), modeling Prime's resistance to slow leaders; as a side effect, proposal slowness measured under Prime is zero even while an attack is ongoing.

## 3 Threat model

- **System.** n = 3f + 1 replicas with f = 1. One replica (replica 0) is malicious.
- **Knowledge.** The malicious replica knows the currently running protocol. This is inherent: a replica must run the current protocol to participate, and the switching decision is reached by all replicas' learning agents, including its own.
- **Capability.** It delays its own proposals when it is the leader. It does not forge messages, break cryptography, or misreport features to the learning agents (data pollution is studied in [1] and excluded here so that any effect comes from timing alone).
- **Leadership.** Replica 0 is the stable leader in PBFT, Zyzzyva, CheapBFT, SBFT and Prime, and leads about one quarter of the time in HotStuff (rotating leader).
- **Budget.** [TODO: finalize] Maximum delay per proposal, bounded by a realistic view-change timeout; and a maximum fraction of wall-clock time during which the attack is on.

> [NOTE] BFTBrain's configs disable view change, so a slow leader is never replaced. A real deployment would replace a leader that exceeds the timeout; our delay bound stands in for this.

## 4 Experimental setup

- **Code.** BFTBrain public code base [3], unmodified protocols and learning algorithm. Local changes: learning-agent start-up race fix, local heap size and JDK path, scripts for unattended runs (`scripts/pilot_run.sh`) and per-minute summaries (`scripts/analyze_pilot.py`).
- **Hardware.** One laptop (Apple M4 Pro, 12 cores, 48 GB); 4 replicas, 1 client and 1 coordinator on localhost.
- **Workload.** BFTBrain's row-1 setting: 4 KB requests, closed loop with 100 clients.
- **Learning.** Default per-transition ("quadratic") random-forest models, 5 warm-up epochs.

> [TODO] Repeat key runs on a multi-machine cluster (CloudLab) if access is granted; single-machine numbers are not comparable in absolute terms to [1].

## 5 Validation: does BFTBrain react to the attack?

We ran BFTBrain with learning enabled, no attack for the first part of the run, and a constant slow-proposal attack afterwards. These runs are single and qualitative.

**Pilot 2: 20 ms delay, attack from 180 s, 800 s total** (`results/pilot-2`, config `exp/pilot/pilot2-20ms.yaml`).

| Time | BFTBrain's behavior | Throughput (req/s) |
| --- | --- | --- |
| 0–60 s | Explores all six protocols | ~13,800 |
| 60–180 s | Settles on Zyzzyva | ~19,000–20,000 |
| 180–660 s | Attack on; tries PBFT, SBFT, CheapBFT, Zyzzyva, HotStuff in turn | ~700–1,300 |
| 660–765 s | Alternates Prime → another protocol → Prime | ~1,300–2,600 |
| 765–800 s | Stays on Prime | ~4,600 |

Throughput per protocol while under attack (`results/pilot-2`):

| Protocol | Avg throughput (req/s) | Epochs | Reason |
| --- | --- | --- | --- |
| Prime | 4,628 | 24 | Fault disabled by design |
| HotStuff | 2,791 | 12 | Replica 0 leads ~1/4 of the time |
| Zyzzyva | 866 | 15 | Replica 0 is the stable leader |
| CheapBFT | 805 | 7 | Same |
| SBFT | 798 | 12 | Same |
| PBFT | 764 | 8 | Same |

**Pilot 1: 100 ms delay, attack from ~360 s** (`results/pilot-1`, config `exp/pilot/pilot-adaptive-attack-half.yaml`). Stable-leader protocols fell from ~20,000 to ~187 req/s, HotStuff to ~730 and Prime stayed at ~4,800. Each attacked epoch lasted ~53 s, so BFTBrain made only 10 decisions in ~6.5 minutes; it reached Prime once and left after one epoch.

**Findings.**

1. *The attack changes which protocol is best.* Zyzzyva is best without attack (~20,000 req/s); Prime is best under attack (~4,600 vs. ≤2,800 for all others). Adaptation is therefore needed, and fixed-protocol baselines face a real trade-off.
2. *BFTBrain reacts and eventually converges.* It leaves Zyzzyva as soon as the attack starts and ends on Prime; it is not permanently misled.
3. *Convergence is slow.* It took about 585 s (~10 min) from attack onset to settling on Prime, with throughput around 1,000 req/s for most of that time, about one fifth of Prime's.
4. *Three mechanisms cause the lag.*
   - **Forced exploration.** Every untried transition is predicted as +∞ and must be tried once; under attack, each try costs a full slow epoch.
   - **Attack invisible under Prime.** Measured proposal slowness under Prime is 0 (learning-agent logs), so from Prime the state looks attack-free and the model favors leaving; it alternates out of Prime until every exit has been tried.
   - **Stretched epochs.** Epochs are a fixed number of sequence numbers, so when throughput drops, each epoch takes longer and decisions slow down exactly when they matter (10–13 s per epoch at 20 ms, ~53 s at 100 ms).
5. *Attack strength.* Locally, even 20 ms reduces stable-leader throughput ~25x. Later experiments add smaller delays.

> [NOTE] Pilot 1's first attempt (`results/pilot-1-failed`) stalled after one epoch because three learning agents crashed on start-up (race creating `data/`); fixed in `code/learning/learning_agent.py`.

## 6 Attack evaluation

> [TODO: Phase 2] Run and fill in.

**Question.** When the attack is turned on and off repeatedly, does adaptive selection do worse than simply fixing one protocol?

**Design.** Slow-proposal attack on for 3 minutes, off for 3 minutes, repeated over ~15 minutes. Three runs: BFTBrain (adaptive), fixed Zyzzyva (best without attack), fixed Prime (immune, slower without attack).

**Metrics.** Average throughput over the run; time to settle after each attack onset and end; number of protocol switches.

**Results.** [TODO]

## 7 Defenses

> [TODO: Phase 3] Implement, evaluate, fill in.

| Mechanism (Section 5) | Defense | Status |
| --- | --- | --- |
| Attack invisible under Prime | Attack memory: add a feature such as the maximum proposal slowness over the last N epochs | Planned (first) |
| Repeated switching | Dwell period (as in BFTide [2]): after an attack-driven switch, stay ≥ k epochs; double k after a rapid re-switch | Planned (first) |
| Forced exploration | Safe exploration: when an attack is detected, explore only transitions with small predicted loss | If time allows |
| Stretched epochs | Time-based epochs, or a cap on epoch duration | If time allows |

**Evaluation plan.** (1) Same on/off attack as Section 6, original vs. improved BFTBrain; (2) no-attack run to confirm normal-case throughput is unchanged; (3) a protocol-aware attacker that knows the defense (e.g., waits out the dwell period).

## 8 Related work

- **BFTBrain** [1]: contextual bandit over six protocols; evaluates fixed, scheduled and randomized faults and data pollution (slight: only SBFT's reward inflated; severe: all values random). None of its adversaries reacts to the selected protocol.
- **BFTide** [2]: switches between leader-based (HotStuff) and leaderless (FIN) protocols with an offline-trained DQN. Its network adversary tracks the current leader, not the selected protocol. It reports that a badly set threshold makes the policy oscillate, and prevents thrashing with a dwell period that doubles after rapid re-switching. No explicit attack budget.
- **Adapt** (Bahsoun, Guerraoui, Shoker): supervised protocol selection; BFTBrain's main baseline. [TODO: read]
- **AutoPilot**: RL-based tuning of BFT parameters with resilience to adversarial manipulation of learning. [TODO: read and position]
- **Adversarial bandits** (e.g., EXP3): theory for bandits whose rewards are chosen by an adaptive adversary. [TODO: one paragraph]

> [NOTE] Novelty wording: not "first protocol-dependent attack" (BFTBrain's SBFT pollution and BFTide's leader tracking are partly dependent). Ours: the adaptation lag as an attack surface, measured against fixed baselines, plus defenses.

## 9 Limitations

- Single machine: no real network delay and shared CPU.
- Pilot results are single runs.
- View change disabled in BFTBrain; delay bound stands in for it.
- Prime's immunity is idealized in BFTBrain (fault fully disabled).

## References

1. C. Wu et al. BFTBrain: Adaptive BFT Consensus with Reinforcement Learning. NSDI 2025. arXiv:2408.06432.
2. S. Bhujel et al. Adaptive Switching Between Leader-Based and Leaderless BFT Protocols. Preprint, 2026. arXiv:2609.31388.
3. BFTBrain source code. https://github.com/JeffersonQin/BFTBrain
