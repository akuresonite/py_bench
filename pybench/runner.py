"""Sweep orchestration.

Two decisions here carry the credibility of the whole exercise:

* **One fresh subprocess per (interpreter, benchmark).** Nothing leaks between
  benchmarks — not caches, not GC state, not interned strings.
* **Benchmark-major iteration.** A sweep takes tens of minutes and machines drift
  thermally across that window. Running benchmark A on all interpreters, then
  benchmark B on all interpreters, spreads that drift evenly instead of charging
  it entirely to whichever version happened to run last.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from . import environment
from .interpreters import DRIVER, Interpreter
from .results import (
    STATUS_DEGRADED,
    STATUS_ERROR,
    STATUS_OK,
    Measurement,
    Sweep,
    speedup,
)

#: Interpreter startup cannot be timed from inside the interpreter, so these two
#: are measured by the runner itself, by timing process spawns.
EXTERNAL_BENCHMARKS = [
    {
        "id": "startup_bare",
        "group": "startup",
        "description": "Interpreter startup with no imports.",
        "args": ["-c", "pass"],
    },
    {
        "id": "startup_imports",
        "group": "startup",
        "description": "Interpreter startup importing json, re, dataclasses, typing.",
        "args": ["-c", "import json, re, dataclasses, typing"],
    },
]

MEASUREMENT_TIMEOUT = 600.0


@dataclass
class RunConfig:
    min_time_ms: float = 50.0
    warmup: int = 2
    rounds: int = 5
    repeats: int = 1
    pin: str | None = None
    groups: list[str] | None = None
    only: list[str] | None = None
    startup_spawns: int = 15
    hash_seed: str = "0"

    def as_dict(self) -> dict[str, Any]:
        return {
            "min_time_ms": self.min_time_ms,
            "warmup": self.warmup,
            "rounds": self.rounds,
            "repeats": self.repeats,
            "pin": self.pin,
            "pin_applied": bool(environment.pin_command(self.pin)),
            "groups": self.groups,
            "only": self.only,
            "startup_spawns": self.startup_spawns,
            "hash_seed": self.hash_seed,
        }


def _child_env(config: RunConfig) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = config.hash_seed
    env.pop("PYTHONSTARTUP", None)
    env.pop("PYTHONPATH", None)
    return env


def build_catalogue(
    entries: list[Interpreter], config: RunConfig
) -> list[dict[str, Any]]:
    """The benchmark list, intersected across the *reference* interpreters.

    A benchmark that fails to import on every CPython build is dropped rather than
    leaving silent holes in the table. Alternative implementations do not get a vote:
    if RustPython cannot run a benchmark, that cell fails and reads as a dash, but the
    benchmark stays in the comparison for everyone else.
    """
    from .interpreters import catalogue as read_catalogue

    voters = [entry for entry in entries if entry.reference] or entries
    per_interpreter: list[dict[str, dict[str, Any]]] = []
    for entry in voters:
        if not entry.available or entry.path is None:
            continue
        found = read_catalogue(entry.path)
        if found is None:
            continue
        per_interpreter.append({item["id"]: item for item in found})

    if not per_interpreter:
        benchmarks: list[dict[str, Any]] = []
    else:
        shared = set(per_interpreter[0])
        for other in per_interpreter[1:]:
            shared &= set(other)
        benchmarks = [
            item for key, item in sorted(per_interpreter[0].items()) if key in shared
        ]

    benchmarks = [
        {"id": item["id"], "group": item["group"], "description": item["description"]}
        for item in benchmarks
    ]
    benchmarks.extend(
        {"id": item["id"], "group": item["group"], "description": item["description"]}
        for item in EXTERNAL_BENCHMARKS
    )
    return _select(benchmarks, config)


def _select(benchmarks: list[dict[str, Any]], config: RunConfig) -> list[dict[str, Any]]:
    selected = benchmarks
    if config.groups:
        wanted = set(config.groups)
        selected = [item for item in selected if item["group"] in wanted]
    if config.only:
        patterns = [pattern.lower() for pattern in config.only]
        selected = [
            item for item in selected
            if any(pattern in item["id"].lower() for pattern in patterns)
        ]
    order = {"startup": 0, "micro": 1, "mini": 2, "threaded": 3}
    selected.sort(key=lambda item: (order.get(item["group"], 9), item["id"]))
    return selected


def _measure_driver(
    entry: Interpreter, benchmark: str, config: RunConfig
) -> tuple[dict[str, Any] | None, str | None]:
    command = environment.pin_command(config.pin) + [
        entry.path,
        DRIVER,
        "run",
        "--id", benchmark,
        "--min-time-ms", str(config.min_time_ms),
        "--warmup", str(config.warmup),
        "--rounds", str(config.rounds),
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True,
            timeout=MEASUREMENT_TIMEOUT, check=False, env=_child_env(config),
        )
    except subprocess.TimeoutExpired:
        return None, "timed out after %.0fs" % MEASUREMENT_TIMEOUT
    except OSError as exc:
        return None, "failed to launch: %s" % exc
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip().splitlines()
        return None, detail[-1][:200] if detail else "exit code %d" % completed.returncode
    try:
        return json.loads(completed.stdout), None
    except json.JSONDecodeError:
        return None, "driver produced no parsable result"


def _measure_startup(
    entry: Interpreter, benchmark: dict[str, Any], config: RunConfig
) -> tuple[dict[str, Any] | None, str | None]:
    command = environment.pin_command(config.pin) + [entry.path] + benchmark["args"]
    env = _child_env(config)
    samples: list[float] = []
    for index in range(config.startup_spawns + config.warmup):
        start = time.perf_counter_ns()
        try:
            completed = subprocess.run(
                command, capture_output=True, timeout=120.0, check=False, env=env
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return None, "spawn failed: %s" % exc
        elapsed = time.perf_counter_ns() - start
        if completed.returncode != 0:
            return None, "interpreter exited %d during startup timing" % completed.returncode
        if index >= config.warmup:
            samples.append(float(elapsed))
    return {
        "loops": 1,
        "values_ns": samples,
        "per_op_ns": samples,
        "median_ns": statistics.median(samples),
        "min_ns": min(samples),
        "mean_ns": statistics.fmean(samples),
        "stddev_ns": statistics.pstdev(samples) if len(samples) > 1 else 0.0,
    }, None


def run_sweep(
    entries: list[Interpreter],
    config: RunConfig,
    on_progress: Callable[[str], None] | None = None,
) -> Sweep:
    """Execute the full matrix and return a populated Sweep."""
    available = [entry for entry in entries if entry.available]
    if not available:
        raise RuntimeError(
            "no interpreters available — run 'pybench install' first"
        )

    host = environment.host_info()
    sweep = Sweep.new(host=host, config=config.as_dict())
    sweep.interpreters = [entry.as_dict() for entry in entries]
    sweep.benchmarks = build_catalogue(available, config)
    if not sweep.benchmarks:
        raise RuntimeError("no benchmarks selected")

    external = {item["id"]: item for item in EXTERNAL_BENCHMARKS}
    governor_name = host.get("governor")
    total = len(sweep.benchmarks) * config.repeats
    index = 0

    for repeat in range(config.repeats):
        for benchmark in sweep.benchmarks:
            index += 1
            cells: dict[str, Measurement] = {}
            for entry in available:
                measurement = _one_measurement(
                    entry, benchmark, external, config, governor_name, repeat
                )
                sweep.measurements.append(measurement)
                cells[entry.key] = measurement
            if on_progress is not None:
                on_progress(_progress_line(index, total, benchmark, cells, available))

    return sweep


def _one_measurement(
    entry: Interpreter,
    benchmark: dict[str, Any],
    external: dict[str, Any],
    config: RunConfig,
    governor_name: str | None,
    repeat: int,
) -> Measurement:
    before = environment.sample()
    if benchmark["id"] in external:
        payload, error = _measure_startup(entry, external[benchmark["id"]], config)
    else:
        payload, error = _measure_driver(entry, benchmark["id"], config)
    after = environment.sample()

    if payload is None:
        return Measurement(
            interpreter=entry.key,
            benchmark=benchmark["id"],
            group=benchmark["group"],
            repeat=repeat,
            status=STATUS_ERROR,
            note=error,
            environment={"before": before.as_dict(), "after": after.as_dict()},
        )

    degraded_reason = environment.is_degraded(before, after, governor_name)
    return Measurement(
        interpreter=entry.key,
        benchmark=benchmark["id"],
        group=benchmark["group"],
        repeat=repeat,
        loops=payload["loops"],
        values_ns=payload["values_ns"],
        per_op_ns=payload["per_op_ns"],
        median_ns=payload["median_ns"],
        min_ns=payload["min_ns"],
        mean_ns=payload["mean_ns"],
        stddev_ns=payload["stddev_ns"],
        status=STATUS_DEGRADED if degraded_reason else STATUS_OK,
        note=degraded_reason,
        environment={"before": before.as_dict(), "after": after.as_dict()},
    )


def _progress_line(
    index: int,
    total: int,
    benchmark: dict[str, Any],
    cells: dict[str, Measurement],
    available: Iterable[Interpreter],
) -> str:
    keys = [entry.key for entry in available]
    ok = [key for key in keys if cells[key].usable]
    label = "%s/%s" % (benchmark["group"], benchmark["id"])
    head = "[%*d/%d] %-34s %d/%d ok" % (
        len(str(total)), index, total, label[:34], len(ok), len(keys)
    )
    if not ok:
        return head
    baseline_key = keys[0]
    baseline = cells[baseline_key]
    fastest_key = min(ok, key=lambda key: cells[key].median_ns)
    if not baseline.usable:
        return "%s   fastest %s" % (head, fastest_key)
    from .results import Cell

    ratio = speedup(
        Cell(median_ns=baseline.median_ns, status=baseline.status),
        Cell(median_ns=cells[fastest_key].median_ns, status=cells[fastest_key].status),
    )
    if ratio is None:
        return "%s   fastest %s" % (head, fastest_key)
    return "%s   fastest %-5s %.2fx vs %s" % (head, fastest_key, ratio, baseline_key)
