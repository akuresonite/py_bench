"""Timing driver for pybench.

This module runs INSIDE each interpreter under test, so it must stay compatible
with Python 3.10 syntax and use nothing outside the standard library.

It speaks a small JSON protocol on stdout:

    python _driver.py probe          -> interpreter metadata
    python _driver.py list           -> benchmark catalogue
    python _driver.py run --id ID    -> one measurement

Exactly one JSON object is written to stdout; benchmarks must never print.
"""

import argparse
import gc
import importlib.util
import json
import os
import sys
import time

try:
    import sysconfig
except ImportError:  # not every Python implementation ships sysconfig
    sysconfig = None

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
BENCH_PREFIX = "bench_"
SETUP_PREFIX = "setup_"
MAX_LOOPS = 1 << 30


def _config_var(name):
    """sysconfig lookup that tolerates implementations without it."""
    if sysconfig is None:
        return None
    try:
        return sysconfig.get_config_var(name)
    except Exception:
        return None


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _mean(values):
    return sum(values) / len(values)


def _pstdev(values):
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return (sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5


def _module_files():
    names = []
    for entry in sorted(os.listdir(BENCH_DIR)):
        if entry.endswith(".py") and not entry.startswith("_"):
            names.append(entry)
    return names


def _load_module(filename):
    name = "pybench_bm_" + filename[:-3]
    path = os.path.join(BENCH_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def discover():
    """Return {bench_id: (module, bench_func, setup_func_or_None, group, doc)}."""
    found = {}
    for filename in _module_files():
        try:
            module = _load_module(filename)
        except Exception as exc:  # a module may legitimately fail on old versions
            found["__error__" + filename] = ("", None, None, "error", repr(exc))
            continue
        group = getattr(module, "GROUP", "micro")
        for attr in sorted(dir(module)):
            if not attr.startswith(BENCH_PREFIX):
                continue
            func = getattr(module, attr)
            if not callable(func):
                continue
            bench_id = attr[len(BENCH_PREFIX):]
            setup = getattr(module, SETUP_PREFIX + bench_id, None)
            doc = (func.__doc__ or "").strip().splitlines()
            found[bench_id] = (filename, func, setup, group, doc[0] if doc else "")
    return found


def probe():
    """Describe the running interpreter: version, GIL state, JIT state."""
    info = {
        "executable": sys.executable,
        "version": ".".join(str(p) for p in sys.version_info[:3]),
        "version_display": sys.version.split()[0],
        "version_full": sys.version.replace("\n", " "),
        "releaselevel": sys.version_info[3],
        "implementation": sys.implementation.name,
        "platform": sys.platform,
        "maxsize_bits": 64 if sys.maxsize > 2 ** 32 else 32,
    }

    # Free-threaded builds set Py_GIL_DISABLED at configure time.
    info["freethreaded_build"] = bool(_config_var("Py_GIL_DISABLED"))
    gil_enabled = None
    is_gil_enabled = getattr(sys, "_is_gil_enabled", None)
    if is_gil_enabled is not None:
        try:
            gil_enabled = bool(is_gil_enabled())
        except Exception:
            gil_enabled = None
    info["gil_enabled"] = gil_enabled

    # JIT: sys._jit exists from 3.14. On 3.13 the only signal is the build flags.
    jit = {"built": False, "available": None, "enabled": None, "active": None,
           "source": "unknown"}
    jit_mod = getattr(sys, "_jit", None)
    if jit_mod is not None:
        jit["source"] = "sys._jit"
        jit["built"] = True
        for key in ("is_available", "is_enabled", "is_active"):
            probe_fn = getattr(jit_mod, key, None)
            if probe_fn is not None:
                try:
                    jit[key[3:]] = bool(probe_fn())
                except Exception:
                    pass
        # sys._jit exists even when the build has no JIT; is_available is the truth.
        if jit.get("available") is False:
            jit["built"] = False
    else:
        cflags = " ".join(
            str(_config_var(var) or "")
            for var in ("PY_CORE_CFLAGS", "CONFIGURE_ARGS", "PY_CFLAGS_NODIST")
        )
        jit["source"] = "sysconfig"
        jit["built"] = ("_Py_JIT" in cflags) or ("--enable-experimental-jit" in cflags)
        jit["available"] = jit["built"]
    info["jit"] = jit

    core_cflags = str(_config_var("PY_CORE_CFLAGS") or "")
    info["config"] = {
        "PGO": "-fprofile-use" in core_cflags,
        "LTO": "-flto" in core_cflags,
        "CC": _config_var("CC"),
    }
    return info


def _make_call(func, setup):
    """Return a zero-argument callable taking a loop count, plus teardown state."""
    if setup is None:
        return func, None
    state = setup()
    return (lambda loops: func(loops, state)), state


def _time_once(call, loops):
    gc.collect()
    start = time.perf_counter_ns()
    call(loops)
    return time.perf_counter_ns() - start


def calibrate(call, min_time_ns, start_loops=1):
    """Grow the loop count until one call takes at least min_time_ns."""
    loops = start_loops
    while True:
        elapsed = _time_once(call, loops)
        if elapsed >= min_time_ns:
            return loops, elapsed
        if loops >= MAX_LOOPS:
            return loops, elapsed
        if elapsed <= 0:
            loops *= 8
        else:
            # Aim just past the target, but never grow more than 16x at a step.
            factor = min(16.0, max(2.0, (min_time_ns / elapsed) * 1.25))
            loops = min(MAX_LOOPS, int(loops * factor) or loops * 2)


def measure(bench_id, min_time_ms, warmup, rounds):
    found = discover()
    if bench_id not in found:
        raise SystemExit("unknown benchmark: %s" % bench_id)
    _filename, func, setup, group, doc = found[bench_id]
    call, _state = _make_call(func, setup)

    min_time_ns = int(min_time_ms * 1_000_000)
    loops, _ = calibrate(call, min_time_ns)

    for _ in range(warmup):
        _time_once(call, loops)

    values = [_time_once(call, loops) for _ in range(rounds)]
    per_op = [value / loops for value in values]
    return {
        "benchmark": bench_id,
        "group": group,
        "description": doc,
        "loops": loops,
        "values_ns": values,
        "per_op_ns": per_op,
        "median_ns": _median(per_op),
        "min_ns": min(per_op),
        "mean_ns": _mean(per_op),
        "stddev_ns": _pstdev(per_op),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="pybench in-interpreter driver")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("probe")
    sub.add_parser("list")
    run = sub.add_parser("run")
    run.add_argument("--id", required=True)
    run.add_argument("--min-time-ms", type=float, default=50.0)
    run.add_argument("--warmup", type=int, default=2)
    run.add_argument("--rounds", type=int, default=5)
    args = parser.parse_args(argv)

    if args.command == "probe":
        payload = probe()
    elif args.command == "list":
        payload = {
            "benchmarks": [
                {"id": key, "group": value[3], "module": value[0], "description": value[4]}
                for key, value in sorted(discover().items())
                if value[1] is not None
            ]
        }
    else:
        payload = measure(args.id, args.min_time_ms, args.warmup, args.rounds)

    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
