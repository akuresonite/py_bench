"""Terminal comparison table."""

from __future__ import annotations

import os
import sys

from ..results import (
    STATUS_DEGRADED,
    Cell,
    Sweep,
    format_duration,
    geometric_mean,
    speedup,
)

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"

FASTER = 1.05
SLOWER = 0.95


def _supports_colour(stream) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(stream, "isatty") and stream.isatty()


class Painter:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def __call__(self, text: str, *codes: str) -> str:
        if not self.enabled or not codes:
            return text
        return "".join(codes) + text + RESET

    def ratio(self, text: str, value: float) -> str:
        if value >= FASTER:
            return self(text, GREEN)
        if value <= SLOWER:
            return self(text, RED)
        return self(text, DIM)


def _standard_keys(sweep: Sweep) -> list[str]:
    return [
        item["key"] for item in sweep.interpreters
        if item.get("available") and not item.get("freethreaded")
        and item.get("reference", True)
    ]


def _alternative_keys(sweep: Sweep) -> list[str]:
    return [
        item["key"] for item in sweep.interpreters
        if item.get("available") and not item.get("reference", True)
    ]


def _freethreaded_pairs(sweep: Sweep) -> list[tuple[str, str]]:
    pairs = []
    for item in sweep.interpreters:
        if not item.get("available") or not item.get("freethreaded"):
            continue
        if not item.get("reference", True):
            continue
        twin = item["minor"]
        twin_entry = sweep.interpreter(twin)
        if twin_entry and twin_entry.get("available"):
            pairs.append((item["key"], twin))
    return pairs


def render(
    sweep: Sweep,
    baseline: str | None = None,
    stream=None,
    colour: bool | None = None,
) -> None:
    stream = stream or sys.stdout
    paint = Painter(_supports_colour(stream) if colour is None else colour)
    keys = _standard_keys(sweep)
    if not keys:
        stream.write("No available interpreters in this sweep.\n")
        return
    baseline = baseline if baseline in keys else keys[0]

    _header(sweep, paint, stream)
    _matrix(sweep, keys, baseline, paint, stream)
    _alternatives(sweep, baseline, paint, stream)
    _freethreading(sweep, paint, stream)
    _summary(sweep, keys, baseline, paint, stream)
    _footnotes(sweep, paint, stream)


def _header(sweep: Sweep, paint: Painter, stream) -> None:
    host = sweep.host
    stream.write("\n%s\n" % paint("pybench sweep %s" % sweep.sweep_id, BOLD))
    stream.write("  host      %s (%s, %s cores, %s GiB)\n" % (
        host.get("model") or host.get("processor") or "unknown",
        host.get("machine"), host.get("cpu_count"), host.get("memory_gib"),
    ))
    stream.write("  system    %s %s | governor %s\n" % (
        host.get("system"), host.get("release"), host.get("governor") or "n/a",
    ))
    config = sweep.config
    stream.write("  protocol  %g ms min, %d warmup, %d rounds, %d repeat(s)%s\n\n" % (
        config.get("min_time_ms"), config.get("warmup"), config.get("rounds"),
        config.get("repeats"),
        ", pinned to cpus %s" % config.get("pin") if config.get("pin_applied") else "",
    ))


def _column_label(sweep: Sweep, key: str) -> str:
    entry = sweep.interpreter(key) or {}
    return key + ("*" if entry.get("prerelease") else "")


def _matrix(sweep: Sweep, keys: list[str], baseline: str, paint: Painter, stream) -> None:
    name_width = max([len(item) for item in sweep.benchmark_ids()] + [20]) + 1
    head = "%-*s %11s" % (name_width, "benchmark", _column_label(sweep, baseline))
    for key in keys:
        if key != baseline:
            head += " %8s" % _column_label(sweep, key)
    stream.write(paint(head, BOLD) + "\n")
    stream.write(paint("  higher is faster; ratios are speedup vs %s" % baseline, DIM) + "\n")

    for group in sweep.groups:
        ids = sweep.benchmark_ids(group)
        if not ids:
            continue
        stream.write(paint("\n  %s\n" % group, BOLD))
        for benchmark in ids:
            base_cell = sweep.cell(benchmark, baseline)
            row = "%-*s %11s" % (
                name_width, benchmark,
                format_duration(base_cell.median_ns) + ("*" if base_cell.status == STATUS_DEGRADED else ""),
            )
            for key in keys:
                if key == baseline:
                    continue
                cell = sweep.cell(benchmark, key)
                ratio = speedup(base_cell, cell)
                if ratio is None:
                    row += " %8s" % paint("—", DIM)
                else:
                    text = "%.2fx" % ratio
                    if cell.status == STATUS_DEGRADED:
                        text += "*"
                    row += " %s" % paint.ratio("%8s" % text, ratio)
            stream.write(row + "\n")


def _alternatives(sweep: Sweep, baseline: str, paint: Painter, stream) -> None:
    """Other Python implementations, kept out of the CPython version ladder."""
    keys = _alternative_keys(sweep)
    if not keys:
        return
    stream.write("\n%s\n" % paint("other implementations", BOLD))
    for key in keys:
        entry = sweep.interpreter(key) or {}
        probe = entry.get("probe") or {}
        stream.write(paint("  %s — %s %s, targeting Python %s\n" % (
            key, probe.get("implementation", "?"),
            probe.get("version_display") or probe.get("version", "?"),
            entry.get("minor") or "?"), DIM))
    stream.write(paint("  times are absolute; ratios compare against %s\n" % baseline, DIM))

    name_width = max([len(item) for item in sweep.benchmark_ids()] + [20]) + 1
    head = "%-*s" % (name_width, "benchmark")
    for key in keys:
        head += " %12s %8s" % (key, "vs " + baseline)
    stream.write(paint(head, BOLD) + "\n")

    for group in sweep.groups:
        ids = sweep.benchmark_ids(group)
        if not ids:
            continue
        stream.write(paint("\n  %s\n" % group, BOLD))
        for benchmark in ids:
            base_cell = sweep.cell(benchmark, baseline)
            row = "%-*s" % (name_width, benchmark)
            for key in keys:
                cell = sweep.cell(benchmark, key)
                if not cell.ok:
                    row += " %12s %8s" % (paint("—", DIM), paint("—", DIM))
                    continue
                ratio = speedup(base_cell, cell)
                row += " %12s" % format_duration(cell.median_ns)
                if ratio is None:
                    row += " %8s" % paint("—", DIM)
                else:
                    row += " %s" % paint.ratio("%8s" % ("%.3gx" % ratio), ratio)
            stream.write(row + "\n")

    failed = {
        benchmark for benchmark in sweep.benchmark_ids()
        for key in keys if not sweep.cell(benchmark, key).ok
    }
    if failed:
        stream.write(paint(
            "\n  %d benchmark(s) could not run on an alternative implementation "
            "and read as '—'.\n" % len(failed), DIM))


def _freethreading(sweep: Sweep, paint: Painter, stream) -> None:
    pairs = _freethreaded_pairs(sweep)
    if not pairs:
        return
    stream.write("\n%s\n" % paint("free-threading cost (each build vs its own GIL twin)", BOLD))
    stream.write(paint("  below 1.00x means the free-threaded build is slower\n", DIM))
    name_width = max([len(item) for item in sweep.benchmark_ids()] + [20]) + 1
    head = "%-*s" % (name_width, "benchmark")
    for freethreaded, twin in pairs:
        head += " %10s" % ("%s/%s" % (freethreaded, twin))
    stream.write(paint(head, BOLD) + "\n")

    for group in sweep.groups:
        ids = sweep.benchmark_ids(group)
        if not ids:
            continue
        stream.write(paint("\n  %s\n" % group, BOLD))
        for benchmark in ids:
            row = "%-*s" % (name_width, benchmark)
            for freethreaded, twin in pairs:
                ratio = speedup(
                    sweep.cell(benchmark, twin), sweep.cell(benchmark, freethreaded)
                )
                if ratio is None:
                    row += " %10s" % paint("—", DIM)
                else:
                    row += " %s" % paint.ratio("%10s" % ("%.2fx" % ratio), ratio)
            stream.write(row + "\n")


def _summary(sweep: Sweep, keys: list[str], baseline: str, paint: Painter, stream) -> None:
    stream.write("\n%s\n" % paint("overall (geometric mean of per-benchmark speedup vs %s)" % baseline, BOLD))
    for group in sweep.groups:
        ids = sweep.benchmark_ids(group)
        if not ids:
            continue
        row = "  %-10s" % group
        for key in keys:
            ratios = [
                speedup(sweep.cell(benchmark, baseline), sweep.cell(benchmark, key))
                for benchmark in ids
            ]
            mean = geometric_mean([value for value in ratios if value])
            if mean is None:
                row += " %9s" % paint("—", DIM)
            else:
                row += " %s" % paint.ratio("%9s" % ("%.2fx" % mean), mean)
        stream.write(row + "\n")
    labels = "  %-10s" % ""
    for key in keys:
        labels += " %9s" % _column_label(sweep, key)
    stream.write(paint(labels, DIM) + "\n")

    threaded = sweep.benchmark_ids("threaded")
    if "threads_parallel" in threaded and "threads_serial" in threaded:
        stream.write("\n%s\n" % paint("thread scaling (serial / parallel — 4 threads, higher is better)", BOLD))
        row = "  %-10s" % "speedup"
        all_keys = [item["key"] for item in sweep.interpreters if item.get("available")]
        for key in all_keys:
            ratio = speedup(
                sweep.cell("threads_parallel", key), sweep.cell("threads_serial", key)
            )
            row += " %9s" % ("%.2fx" % (1 / ratio) if ratio else "—")
        stream.write(row + "\n")
        labels = "  %-10s" % ""
        for key in all_keys:
            labels += " %9s" % _column_label(sweep, key)
        stream.write(paint(labels, DIM) + "\n")


def _footnotes(sweep: Sweep, paint: Painter, stream) -> None:
    lines = []
    prerelease = [
        item["key"] for item in sweep.interpreters
        if item.get("available") and item.get("prerelease")
    ]
    if prerelease:
        lines.append("* %s %s; the numbers are provisional."
                     % (", ".join(prerelease),
                        "is a pre-release" if len(prerelease) == 1
                        else "are pre-releases"))
    degraded = sweep.degraded_count()
    if degraded:
        lines.append("* %d measurement(s) ran in degraded conditions and are marked '*':"
                     % degraded)
        for note in sweep.notes()[:4]:
            lines.append("    - %s" % note)
    errors = sweep.error_count()
    if errors:
        lines.append("! %d measurement(s) failed and are shown as '—'." % errors)
    unavailable = [
        item for item in sweep.interpreters if not item.get("available")
    ]
    for item in unavailable:
        lines.append("! %s unavailable: %s" % (item["key"], item.get("reason")))
    if lines:
        stream.write("\n")
        for line in lines:
            stream.write(paint(line, YELLOW if line.startswith("!") else DIM) + "\n")
    stream.write("\n")
