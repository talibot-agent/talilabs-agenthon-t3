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


    # ---- v2: cheaper (but exactly equivalent) copies in event logging ----
    from copy import deepcopy
    from enum import Enum
    import numpy as _np
    LimitOrder, MarketOrder = o.LimitOrder, o.MarketOrder
    _fmt = fast_fmt_ts

    def to_dict(self):
        """== deepcopy(self).__dict__ with time_placed formatted (same keys, same order)."""
        t = type(self)
        tag = self.tag
        if tag is not None:
            tag = deepcopy(tag)
        if t is LimitOrder:
            return {"agent_id": self.agent_id, "time_placed": _fmt(self.time_placed),
                    "symbol": self.symbol, "quantity": self.quantity, "side": self.side,
                    "order_id": self.order_id, "fill_price": self.fill_price, "tag": tag,
                    "limit_price": self.limit_price, "is_hidden": self.is_hidden,
                    "is_price_to_comply": self.is_price_to_comply,
                    "insert_by_id": self.insert_by_id, "is_post_only": self.is_post_only}
        if t is MarketOrder:
            return {"agent_id": self.agent_id, "time_placed": _fmt(self.time_placed),
                    "symbol": self.symbol, "quantity": self.quantity, "side": self.side,
                    "order_id": self.order_id, "fill_price": self.fill_price, "tag": tag}
        d = deepcopy(self).__dict__
        d["time_placed"] = _fmt(self.time_placed)
        return d
    o.Order.to_dict = to_dict

    _ATOMS = (int, float, str, bool, type(None), Enum, _np.integer, _np.floating, _np.bool_)
    import abides_core.agent as _ag


    # ---- v2: exact fast order / message copies ----
    _new = object.__new__

    def lo_deepcopy(self, memodict={}):
        tag = self.tag
        n = _new(LimitOrder)
        d = n.__dict__
        d["agent_id"] = self.agent_id; d["time_placed"] = self.time_placed
        d["symbol"] = self.symbol; d["quantity"] = self.quantity; d["side"] = self.side
        d["order_id"] = self.order_id; d["fill_price"] = self.fill_price
        d["tag"] = None if tag is None else deepcopy(tag)
        d["limit_price"] = self.limit_price; d["is_hidden"] = self.is_hidden
        d["is_price_to_comply"] = self.is_price_to_comply
        d["insert_by_id"] = self.insert_by_id; d["is_post_only"] = self.is_post_only
        return n

    def mo_deepcopy(self, memodict={}):
        tag = self.tag
        n = _new(MarketOrder)
        d = n.__dict__
        d["agent_id"] = self.agent_id; d["time_placed"] = self.time_placed
        d["symbol"] = self.symbol; d["quantity"] = self.quantity; d["side"] = self.side
        d["order_id"] = self.order_id; d["fill_price"] = self.fill_price
        d["tag"] = None if tag is None else deepcopy(tag)
        return n
    LimitOrder.__deepcopy__ = lo_deepcopy
    MarketOrder.__deepcopy__ = mo_deepcopy

    _ORD = {LimitOrder: lo_deepcopy, MarketOrder: mo_deepcopy}

    def fast_deepcopy(x, memo=None):
        f = _ORD.get(type(x))
        if f is not None:
            return f(x)
        return deepcopy(x, memo)
    import abides_markets.order_book as _ob
    _ob.deepcopy = fast_deepcopy

    import abides_core.message as _msg
    _fastmsg = {}

    def _msg_ok(cls):
        r = _fastmsg.get(cls)
        if r is None:
            r = (issubclass(cls, _msg.Message) and "__slots__" not in cls.__dict__
                 and getattr(cls, "__deepcopy__", None) is None
                 and getattr(cls, "__setstate__", None) is None
                 and cls.__reduce_ex__ is object.__reduce_ex__
                 and cls.__reduce__ is object.__reduce__
                 and cls.__getstate__ is object.__getstate__)
            _fastmsg[cls] = r
        return r

    def msg_copy(m):
        """== copy.deepcopy(m) for plain dataclass messages (state = __dict__)."""
        cls = type(m)
        n = _new(cls)
        memo = {id(m): n}
        nd = n.__dict__
        for k, v in m.__dict__.items():
            if isinstance(v, _ATOMS):
                nd[k] = v
            else:
                f = _ORD.get(type(v))
                nd[k] = f(v) if f is not None else deepcopy(v, memo)
        return n

    def logEvent(self, event_type, event="", append_summary_log=False, deepcopy_event=True):
        if not self.log_events:
            return
        if deepcopy_event:
            if isinstance(event, _ATOMS):
                pass  # immutable: deepcopy would be an equal value
            elif type(event) is dict and all(isinstance(v, _ATOMS) for v in event.values()) \
                    and all(type(k) is str for k in event):
                event = dict(event)
            elif _msg_ok(type(event)):
                event = msg_copy(event)
            else:
                event = deepcopy(event)
        self.log.append((self.current_time, event_type, event))
        if append_summary_log:
            self.kernel.append_summary_log(self.id, event_type, event)
    _orig = _ag.Agent.logEvent
    _ag.Agent.logEvent = logEvent


    # ---- v2: leaner parse_logs_df (same rows, same key order, same dtypes) ----
    import pandas as _pd
    _i64 = (int, _np.int64)

    def parse_logs_df(end_state):
        dfs = []
        for agent in end_state["agents"]:
            aid, atype = agent.id, agent.type
            messages = []
            app = messages.append
            for t, etype, event in agent.log:
                m = {"EventTime": t if isinstance(t, _i64) else 0, "EventType": etype}
                if event == None:  # noqa: E711  (kept identical to upstream semantics)
                    event = {"EmptyEvent": True}
                elif not isinstance(event, dict):
                    event = {"ScalarEventValue": event}
                m.update(event)
                if m.get("agent_id") == None:  # noqa: E711
                    m["agent_id"] = aid
                m["agent_type"] = atype
                app(m)
            dfs.append(_pd.DataFrame(messages))
        return _pd.concat(dfs)
    u.parse_logs_df = parse_logs_df
    import abides_fork.trace as _tr
    _tr.parse_logs_df = parse_logs_df

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
