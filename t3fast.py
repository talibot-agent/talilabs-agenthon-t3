"""Tali Labs Track 3 speed layer (semantics-preserving).

Applied before any simulation. Every patch here is observation-neutral: it changes
no RNG draw, no event ordering and no simulation logic, so traces stay byte-identical
to the pinned ABIDES reference (verified on all public units, see README).

Written by Tali (an AI agent) for team Tali Labs.
"""
from __future__ import annotations

import gc
import os
import warnings
from datetime import datetime, timedelta, timezone

warnings.simplefilter("ignore")  # stderr spam (str(order) formatting is still cheap below)

_EPOCH = datetime(1970, 1, 1)
_cache: dict[int, str] = {}


def fast_fmt_ts(timestamp) -> str:
    """Exact equivalent of pd.Timestamp(ts, unit='ns').strftime('%Y-%m-%d %H:%M:%S')."""
    sec = int(timestamp) // 1_000_000_000
    s = _cache.get(sec)
    if s is None:
        s = (_EPOCH + timedelta(seconds=sec)).strftime("%Y-%m-%d %H:%M:%S")
        if len(_cache) < 1_000_000:
            _cache[sec] = s
    return s


def apply() -> None:
    import abides_core.utils as u
    import abides_core.agent as a
    import abides_core.kernel as k
    import abides_markets.orders as o
    import abides_markets.agents.trading_agent as ta

    for m in (u, a, k, o, ta):
        if getattr(m, "fmt_ts", None) is not None:
            m.fmt_ts = fast_fmt_ts

    import abides_fork.config as cfg

    cls = None
    for v in vars(cfg).values():
        if isinstance(v, type) and "get_latency" in vars(v) and "_min_ns" in v.__init__.__code__.co_names:
            cls = v
    if cls is not None:
        def get_latency(self, sender_id, recipient_id):
            if sender_id == recipient_id:
                return 0
            model = self._model
            rs = self.random_state
            if model == "log_normal":
                value = rs.lognormal(mean=self._mu, sigma=self._sigma)
            elif model == "uniform":
                value = rs.uniform(self._min_ns, self._max_ns)
            elif model == "pareto":
                base = self._min_ns if self._min_ns > 0 else 1.0
                value = base * (1.0 + rs.pareto(self._alpha))
            else:
                value = self._mean_ns
            value = float(value)
            # np.clip(v, lo, hi) == minimum(maximum(v, lo), hi), NaN-propagating
            lo, hi = self._min_ns, self._max_ns
            if value < lo:
                value = lo
            if value > hi:
                value = hi
            return int(round(value))
        cls.get_latency = get_latency

    # The simulator allocates millions of short-lived objects; the cyclic GC only
    # costs time here (16G memory cap per card). Freeze startup objects, raise thresholds.
    gc.freeze()
    gc.set_threshold(200_000, 50, 100)


def cpu_quota() -> int:
    try:
        q, p = open("/sys/fs/cgroup/cpu.max").read().split()
        if q != "max":
            return max(1, int(int(q) // int(p)))
    except Exception:
        pass
    try:
        return len(os.sched_getaffinity(0))
    except Exception:
        return os.cpu_count() or 1
