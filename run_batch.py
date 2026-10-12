"""Parallel simulate-batch: each sub-scenario runs in its own forked process, so its
output is exactly its isolated run (counters reset, RNG re-seeded per sub)."""
import json, pathlib, sys, time, argparse, multiprocessing as mp
import t3fast
t3fast.apply()
from abides_fork.simulate import simulate


def _one(args):
    sub_path, out = args
    # ABIDES' kernel creates ./log/<epoch-seconds> with makedirs(exist_ok=False); parallel
    # sub-runs starting in the same second would collide. Give each process its own cwd.
    import os, tempfile
    os.chdir(tempfile.mkdtemp(prefix="t3sub-"))
    return simulate(sub_path, out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="simulate-batch")
    ap.add_argument("verb", nargs="?", default="simulate-batch", choices=["simulate-batch"])
    ap.add_argument("--batch-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    batch_dir, out_dir = pathlib.Path(a.batch_dir).resolve(), pathlib.Path(a.out_dir).resolve()
    subs = sorted(batch_dir.glob("*.json"))
    if not subs:
        raise SystemExit(f"simulate-batch: no sub-scenarios (*.json) found in {batch_dir}")
    jobs = [(p, out_dir / p.stem / "trace.parquet") for p in subs]
    t0 = time.perf_counter()
    n = min(len(jobs), t3fast.cpu_quota())
    if n > 1:
        ctx = mp.get_context("fork")
        with ctx.Pool(n, maxtasksperchild=1) as pool:
            evs = pool.map(_one, jobs, chunksize=1)
    else:
        evs = [_one(j) for j in jobs]
    wall = time.perf_counter() - t0
    total = sum(int(e["n_events"]) for e in evs)
    be = {
        "n_scenarios": len(subs),
        "total_events": total,
        "wall_clock_sec": float(wall),
        "events_per_sec": float(total / wall) if wall > 0 else 0.0,
        "peak_memory_bytes": sum(int(e.get("peak_memory_bytes", 0)) for e in evs),
        "gpu_seconds": 0.0,
        "per_scenario": [{"sub": p.stem, "n_events": int(e["n_events"]), "trace_sha256": e["trace_sha256"]} for p, e in zip(subs, evs)],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "batch_events.json").write_text(json.dumps(be, indent=2) + "\n")
    print(json.dumps(be))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
