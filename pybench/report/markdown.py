"""Markdown report — the same tables as the terminal view, diffable in git."""

from __future__ import annotations

from ..results import (
    STATUS_DEGRADED,
    Sweep,
    format_duration,
    geometric_mean,
    speedup,
)


def _standard_keys(sweep: Sweep) -> list[str]:
    return [
        item["key"] for item in sweep.interpreters
        if item.get("available") and not item.get("freethreaded")
    ]


def _freethreaded_pairs(sweep: Sweep) -> list[tuple[str, str]]:
    pairs = []
    for item in sweep.interpreters:
        if not item.get("available") or not item.get("freethreaded"):
            continue
        twin = sweep.interpreter(item["minor"])
        if twin and twin.get("available"):
            pairs.append((item["key"], item["minor"]))
    return pairs


def _label(sweep: Sweep, key: str) -> str:
    entry = sweep.interpreter(key) or {}
    return "%s%s" % (key, " ⚠" if entry.get("prerelease") else "")


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def render(sweep: Sweep, baseline: str | None = None) -> str:
    keys = _standard_keys(sweep)
    if not keys:
        return "# pybench\n\nNo available interpreters in this sweep.\n"
    baseline = baseline if baseline in keys else keys[0]

    out: list[str] = []
    out.append("# Python version speed benchmark")
    out.append("")
    out.append("Sweep `%s` — %s" % (sweep.sweep_id, sweep.created_at))
    out.append("")
    out.extend(_environment_section(sweep))
    out.extend(_interpreter_section(sweep))
    out.extend(_summary_section(sweep, keys, baseline))
    out.extend(_matrix_section(sweep, keys, baseline))
    out.extend(_freethreading_section(sweep))
    out.extend(_thread_scaling_section(sweep))
    out.extend(_caveats_section(sweep))
    return "\n".join(out) + "\n"


def _environment_section(sweep: Sweep) -> list[str]:
    host = sweep.host
    config = sweep.config
    lines = ["## Environment", ""]
    lines.append(_row(["Property", "Value"]))
    lines.append(_row(["---", "---"]))
    rows = [
        ("Machine", host.get("model") or host.get("processor") or "unknown"),
        ("Architecture", host.get("machine")),
        ("Cores", host.get("cpu_count")),
        ("Memory", "%s GiB" % host.get("memory_gib") if host.get("memory_gib") else "unknown"),
        ("System", "%s %s" % (host.get("system"), host.get("release"))),
        ("CPU governor", host.get("governor") or "not exposed"),
        ("Protocol", "%g ms minimum, %d warmup, %d rounds, %d repeat(s)" % (
            config.get("min_time_ms"), config.get("warmup"),
            config.get("rounds"), config.get("repeats"))),
        ("CPU pinning", config.get("pin") if config.get("pin_applied") else "not used"),
        ("PYTHONHASHSEED", config.get("hash_seed")),
    ]
    for name, value in rows:
        lines.append(_row([name, str(value)]))
    lines.append("")
    return lines


def _interpreter_section(sweep: Sweep) -> list[str]:
    lines = ["## Interpreters", ""]
    lines.append(_row(["Key", "Version", "Build", "GIL", "JIT", "Source", "Status"]))
    lines.append(_row(["---"] * 7))
    for item in sweep.interpreters:
        probe = item.get("probe") or {}
        jit = probe.get("jit") or {}
        if not item.get("available"):
            lines.append(_row([
                item["key"], "—", "—", "—", "—", "—",
                "unavailable: %s" % (item.get("reason") or "unknown"),
            ]))
            continue
        gil = probe.get("gil_enabled")
        if item.get("freethreaded"):
            gil_text = "disabled" if gil is False else "enabled"
        else:
            gil_text = "enabled"
        if jit.get("built"):
            jit_text = "enabled" if jit.get("enabled") else "built, disabled"
        else:
            jit_text = "not built"
        lines.append(_row([
            item["key"],
            probe.get("version_display") or probe.get("version", "?"),
            "free-threaded" if item.get("freethreaded") else "standard",
            gil_text,
            jit_text,
            item.get("source", "uv"),
            "pre-release ⚠" if item.get("prerelease") else "ok",
        ]))
    lines.append("")
    return lines


def _summary_section(sweep: Sweep, keys: list[str], baseline: str) -> list[str]:
    lines = ["## Summary", ""]
    lines.append("Geometric mean of per-benchmark speedup against `%s`. "
                 "Higher is faster." % baseline)
    lines.append("")
    lines.append(_row(["Group"] + [_label(sweep, key) for key in keys]))
    lines.append(_row(["---"] * (len(keys) + 1)))
    for group in sweep.groups:
        ids = sweep.benchmark_ids(group)
        if not ids:
            continue
        cells = [group]
        for key in keys:
            ratios = [
                speedup(sweep.cell(benchmark, baseline), sweep.cell(benchmark, key))
                for benchmark in ids
            ]
            mean = geometric_mean([value for value in ratios if value])
            cells.append("%.2fx" % mean if mean else "—")
        lines.append(_row(cells))
    lines.append("")
    return lines


def _matrix_section(sweep: Sweep, keys: list[str], baseline: str) -> list[str]:
    lines = ["## Per-benchmark results", ""]
    lines.append("The `%s` column is an absolute per-operation time; every other column "
                 "is a speedup ratio against it." % baseline)
    lines.append("")
    for group in sweep.groups:
        ids = sweep.benchmark_ids(group)
        if not ids:
            continue
        lines.append("### %s" % group)
        lines.append("")
        header = ["Benchmark", _label(sweep, baseline)]
        header += [_label(sweep, key) for key in keys if key != baseline]
        lines.append(_row(header))
        lines.append(_row(["---"] * len(header)))
        for benchmark in ids:
            base_cell = sweep.cell(benchmark, baseline)
            cells = [
                "`%s`" % benchmark,
                format_duration(base_cell.median_ns)
                + ("\\*" if base_cell.status == STATUS_DEGRADED else ""),
            ]
            for key in keys:
                if key == baseline:
                    continue
                cell = sweep.cell(benchmark, key)
                ratio = speedup(base_cell, cell)
                if ratio is None:
                    cells.append("—")
                else:
                    cells.append("%.2fx%s" % (
                        ratio, "\\*" if cell.status == STATUS_DEGRADED else ""))
            lines.append(_row(cells))
        lines.append("")
    return lines


def _freethreading_section(sweep: Sweep) -> list[str]:
    pairs = _freethreaded_pairs(sweep)
    if not pairs:
        return []
    lines = ["## Free-threading cost", ""]
    lines.append("Each free-threaded build against its own GIL twin. Below `1.00x` means "
                 "the free-threaded build is slower at that benchmark.")
    lines.append("")
    header = ["Benchmark"] + ["%s / %s" % pair for pair in pairs]
    lines.append(_row(header))
    lines.append(_row(["---"] * len(header)))
    for group in sweep.groups:
        for benchmark in sweep.benchmark_ids(group):
            cells = ["`%s`" % benchmark]
            for freethreaded, twin in pairs:
                ratio = speedup(
                    sweep.cell(benchmark, twin), sweep.cell(benchmark, freethreaded)
                )
                cells.append("%.2fx" % ratio if ratio else "—")
            lines.append(_row(cells))
    lines.append("")
    overall = ["**geometric mean**"]
    for freethreaded, twin in pairs:
        ratios = [
            speedup(sweep.cell(benchmark, twin), sweep.cell(benchmark, freethreaded))
            for benchmark in sweep.benchmark_ids()
            if not benchmark.startswith("threads_")
        ]
        mean = geometric_mean([value for value in ratios if value])
        overall.append("**%.2fx**" % mean if mean else "—")
    lines.insert(len(lines) - 1, _row(overall))
    return lines


def _thread_scaling_section(sweep: Sweep) -> list[str]:
    ids = sweep.benchmark_ids("threaded")
    if "threads_parallel" not in ids or "threads_serial" not in ids:
        return []
    keys = [item["key"] for item in sweep.interpreters if item.get("available")]
    lines = ["## Thread scaling", ""]
    lines.append("Identical CPU work run serially and across four threads. The ratio is "
                 "the achieved parallel speedup; GIL builds are expected near `1.00x`.")
    lines.append("")
    lines.append(_row(["Interpreter", "Parallel speedup"]))
    lines.append(_row(["---", "---"]))
    for key in keys:
        ratio = speedup(
            sweep.cell("threads_parallel", key), sweep.cell("threads_serial", key)
        )
        lines.append(_row([_label(sweep, key), "%.2fx" % (1 / ratio) if ratio else "—"]))
    lines.append("")
    return lines


def _caveats_section(sweep: Sweep) -> list[str]:
    lines = ["## Caveats", ""]
    prerelease = [
        item["key"] for item in sweep.interpreters
        if item.get("available") and item.get("prerelease")
    ]
    if prerelease:
        lines.append("- ⚠ %s %s a pre-release build; the numbers are provisional and may "
                     "change before final release."
                     % (", ".join(prerelease), "is" if len(prerelease) == 1 else "are"))
    if sweep.degraded_count():
        lines.append("- %d measurement(s) ran in degraded conditions and are marked `*`:"
                     % sweep.degraded_count())
        for note in sweep.notes():
            lines.append("  - %s" % note)
    if sweep.error_count():
        lines.append("- %d measurement(s) failed and appear as `—`." % sweep.error_count())
    for item in sweep.interpreters:
        if not item.get("available"):
            lines.append("- `%s` was not benchmarked: %s"
                         % (item["key"], item.get("reason")))
    lines.append("- Free-threaded builds differ from their GIL twins in build "
                 "configuration as well as in the GIL, so the comparison measures both.")
    lines.append("- Results describe the machine that produced them and do not transfer "
                 "to other hardware.")
    lines.append("")
    return lines
