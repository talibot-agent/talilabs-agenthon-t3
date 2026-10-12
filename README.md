# Tali Labs — Agenthon 2026 Track 3 (Simulation) entry

> **AI disclosure:** this entry was built autonomously by **Tali, an AI agent**, for team Tali Labs (#765), human entrant Mykel Nelson. Based on the organizers' ABIDES baseline (see LICENSE files and THIRD-PARTY-NOTICES.md).
Built by Tali (an AI agent) for team Tali Labs (#765), human entrant Mykel Nelson.

## What it is
The organizers' pinned ABIDES baseline (built from track3-simulation-public/baselines, tag `t3base`)
plus a semantics-preserving speed layer (`t3fast.py`):
- exact fast `fmt_ts` (cached per second; the old one was eager pandas formatting in debug log args)
- `get_latency` without numpy `np.clip` overhead (same clip semantics, same RNG draws)
- GC freeze + higher thresholds; precompiled bytecode; warnings silenced
- `simulate-batch` runs sub-scenarios in parallel forked processes (one per cgroup CPU), each isolated
## Validation (`./validate.sh IMAGE CSV`)
71/71 public units: trace.parquet AND message_trace.parquet byte-identical to the references (val_v1.csv).
Container-time throughput (create→exit, --cpus 4), geomean: v1 = 10,657 events/s. Baseline: see val_base.csv.
## Submit
1. push image to a public registry, get digest  2. fill submission.json (fixture simulation_dev.json)
