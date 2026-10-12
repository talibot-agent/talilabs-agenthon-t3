"""Lazy stand-in for scipy.spatial(.distance): abides_markets.utils imports pdist/squareform
at module load (~0.25 s of scipy imports) but only calls them for geographic latency models.
The real modules are imported on first use, so behaviour is unchanged. (Tali Labs, AI-authored)"""
import sys, types


def _real():
    for k in ("scipy.spatial.distance", "scipy.spatial"):
        if getattr(sys.modules.get(k), "_t3_stub", False):
            del sys.modules[k]
    import scipy.spatial.distance as d
    return d


def _lazy(name):
    def f(*a, **k):
        return getattr(_real(), name)(*a, **k)
    f.__name__ = name
    return f


def _ga(modname):
    def __getattr__(n):
        if n.startswith("__"):
            raise AttributeError(n)
        _real()
        return getattr(sys.modules[modname], n)
    return __getattr__


def install():
    if "scipy.spatial" in sys.modules:
        return
    import scipy  # light top-level package (no submodules)
    sp = types.ModuleType("scipy.spatial"); sp._t3_stub = True; sp.__path__ = []
    dist = types.ModuleType("scipy.spatial.distance"); dist._t3_stub = True
    dist.pdist = _lazy("pdist"); dist.squareform = _lazy("squareform")
    dist.__getattr__ = _ga("scipy.spatial.distance")
    sp.distance = dist
    sp.__getattr__ = _ga("scipy.spatial")
    sys.modules["scipy.spatial"] = sp; sys.modules["scipy.spatial.distance"] = dist
