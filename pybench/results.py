"""Results schema and aggregation.

The JSON document written by a sweep is the contract between the runner and the
reporters: reporters read it and never re-measure. Every field a reporter needs
must therefore be recorded at measurement time.
"""

from __future__ import annotations

import json
import math
import os
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

SCHEMA_VERSION = 1

STATUS_OK = "ok"
STATUS_DEGRADED = "degraded"
STATUS_ERROR = "error"


@dataclass
class Measurement:
    interpreter: str
    benchmark: str
    group: str
    repeat: int = 0
    loops: int = 0
    values_ns: list[float] = field(default_factory=list)
    per_op_ns: list[float] = field(default_factory=list)
    median_ns: float | None = None
    min_ns: float | None = None
    mean_ns: float | None = None
    stddev_ns: float | None = None
    status: str = STATUS_OK
    note: str | None = None
    environment: dict[str, Any] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return self.status != STATUS_ERROR and self.median_ns is not None


@dataclass
class Sweep:
    sweep_id: str
    created_at: str
    host: dict[str, Any]
    config: dict[str, Any]
    interpreters: list[dict[str, Any]] = field(default_factory=list)
    benchmarks: list[dict[str, Any]] = field(default_factory=list)
    measurements: list[Measurement] = field(default_factory=list)
    schema: int = SCHEMA_VERSION

    # -- construction ----------------------------------------------------

    @classmethod
    def new(cls, host: dict[str, Any], config: dict[str, Any]) -> "Sweep":
        now = datetime.now(timezone.utc)
        return cls(
            sweep_id=now.strftime("%Y%m%dT%H%M%SZ"),
            created_at=now.isoformat(timespec="seconds"),
            host=host,
            config=config,
        )

    # -- persistence -----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "sweep_id": self.sweep_id,
            "created_at": self.created_at,
            "host": self.host,
            "config": self.config,
            "interpreters": self.interpreters,
            "benchmarks": self.benchmarks,
            "measurements": [asdict(item) for item in self.measurements],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Sweep":
        schema = data.get("schema")
        if schema != SCHEMA_VERSION:
            raise ValueError(
                "unsupported results schema %r (this build reads %d)"
                % (schema, SCHEMA_VERSION)
            )
        sweep = cls(
            sweep_id=data["sweep_id"],
            created_at=data["created_at"],
            host=data.get("host", {}),
            config=data.get("config", {}),
            interpreters=data.get("interpreters", []),
            benchmarks=data.get("benchmarks", []),
            schema=schema,
        )
        sweep.measurements = [
            Measurement(**item) for item in data.get("measurements", [])
        ]
        return sweep

    def save(self, path: str) -> str:
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, sort_keys=False)
            handle.write("\n")
        return path

    @classmethod
    def load(cls, path: str) -> "Sweep":
        with open(path, "r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    # -- views -----------------------------------------------------------

    @property
    def interpreter_keys(self) -> list[str]:
        return [item["key"] for item in self.interpreters]

    def interpreter(self, key: str) -> dict[str, Any] | None:
        for item in self.interpreters:
            if item["key"] == key:
                return item
        return None

    def benchmark_ids(self, group: str | None = None) -> list[str]:
        return [
            item["id"] for item in self.benchmarks
            if group is None or item.get("group") == group
        ]

    @property
    def groups(self) -> list[str]:
        seen: list[str] = []
        for item in self.benchmarks:
            group = item.get("group", "micro")
            if group not in seen:
                seen.append(group)
        return seen

    def cell(self, benchmark: str, interpreter: str) -> "Cell":
        """Aggregate every repeat of one benchmark on one interpreter."""
        matches = [
            item for item in self.measurements
            if item.benchmark == benchmark and item.interpreter == interpreter
        ]
        return Cell.from_measurements(matches)

    def degraded_count(self) -> int:
        return sum(1 for item in self.measurements if item.status == STATUS_DEGRADED)

    def error_count(self) -> int:
        return sum(1 for item in self.measurements if item.status == STATUS_ERROR)

    def notes(self) -> list[str]:
        seen: list[str] = []
        for item in self.measurements:
            if item.note and item.note not in seen:
                seen.append(item.note)
        return seen


@dataclass
class Cell:
    """One benchmark on one interpreter, aggregated across repeats."""

    median_ns: float | None = None
    min_ns: float | None = None
    stddev_ns: float | None = None
    repeats: int = 0
    status: str = STATUS_ERROR
    note: str | None = None

    @classmethod
    def from_measurements(cls, items: Iterable[Measurement]) -> "Cell":
        items = list(items)
        usable = [item for item in items if item.usable]
        if not usable:
            note = next((item.note for item in items if item.note), None)
            return cls(status=STATUS_ERROR, note=note, repeats=len(items))
        medians = [item.median_ns for item in usable if item.median_ns is not None]
        mins = [item.min_ns for item in usable if item.min_ns is not None]
        status = (
            STATUS_DEGRADED
            if any(item.status == STATUS_DEGRADED for item in usable)
            else STATUS_OK
        )
        return cls(
            median_ns=statistics.median(medians),
            min_ns=min(mins) if mins else None,
            stddev_ns=statistics.pstdev(medians) if len(medians) > 1 else
            (usable[0].stddev_ns or 0.0),
            repeats=len(usable),
            status=status,
            note=next((item.note for item in usable if item.note), None),
        )

    @property
    def ok(self) -> bool:
        return self.median_ns is not None


def speedup(baseline: Cell, other: Cell) -> float | None:
    """How many times faster ``other`` is than ``baseline``.

    Greater than 1 means faster. Returns None when either side is missing.
    """
    if not baseline.ok or not other.ok:
        return None
    if not other.median_ns:
        return None
    return baseline.median_ns / other.median_ns


def geometric_mean(values: Iterable[float]) -> float | None:
    """Geometric mean — the correct average for a set of speedup ratios."""
    usable = [value for value in values if value and value > 0]
    if not usable:
        return None
    return math.exp(sum(math.log(value) for value in usable) / len(usable))


def format_duration(nanoseconds: float | None) -> str:
    """Render a per-operation duration with a sensible unit."""
    if nanoseconds is None:
        return "—"
    if nanoseconds < 1_000:
        return "%.1f ns" % nanoseconds
    if nanoseconds < 1_000_000:
        return "%.2f us" % (nanoseconds / 1_000)
    if nanoseconds < 1_000_000_000:
        return "%.2f ms" % (nanoseconds / 1_000_000)
    return "%.2f s" % (nanoseconds / 1_000_000_000)
