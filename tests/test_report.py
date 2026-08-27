"""Terminal and markdown rendering."""

import io

from pybench.report import markdown as markdown_report
from pybench.report import table as table_report
from pybench.results import STATUS_DEGRADED, STATUS_ERROR, STATUS_OK, Measurement, Sweep

TIMES = {
    ("call_simple", "3.10"): 200.0,
    ("call_simple", "3.14"): 100.0,
    ("call_simple", "3.15"): 80.0,
    ("call_simple", "3.14t"): 125.0,
    ("threads_serial", "3.10"): 400.0,
    ("threads_serial", "3.14"): 400.0,
    ("threads_serial", "3.15"): 400.0,
    ("threads_serial", "3.14t"): 400.0,
    ("threads_parallel", "3.10"): 400.0,
    ("threads_parallel", "3.14"): 400.0,
    ("threads_parallel", "3.15"): 400.0,
    ("threads_parallel", "3.14t"): 100.0,
}


def build_sweep():
    sweep = Sweep.new(
        host={"model": "Test Box", "machine": "aarch64", "cpu_count": 4,
              "memory_gib": 8.0, "system": "Linux", "release": "6.0",
              "governor": "performance", "host_python": "3.13.5"},
        config={"min_time_ms": 50.0, "warmup": 2, "rounds": 5, "repeats": 1,
                "pin": None, "pin_applied": False, "hash_seed": "0"},
    )
    sweep.interpreters = [
        {"key": "3.10", "minor": "3.10", "freethreaded": False, "prerelease": False,
         "available": True, "source": "uv",
         "probe": {"version": "3.10.20", "version_display": "3.10.20",
                   "gil_enabled": True, "jit": {"built": False}}},
        {"key": "3.14", "minor": "3.14", "freethreaded": False, "prerelease": False,
         "available": True, "source": "uv",
         "probe": {"version": "3.14.4", "version_display": "3.14.4",
                   "gil_enabled": True, "jit": {"built": True, "enabled": False}}},
        {"key": "3.15", "minor": "3.15", "freethreaded": False, "prerelease": True,
         "available": True, "source": "uv",
         "probe": {"version": "3.15.0", "version_display": "3.15.0a8",
                   "gil_enabled": True, "jit": {"built": True, "enabled": False}}},
        {"key": "3.14t", "minor": "3.14", "freethreaded": True, "prerelease": False,
         "available": True, "source": "uv",
         "probe": {"version": "3.14.4", "version_display": "3.14.4",
                   "gil_enabled": False, "jit": {"built": False}}},
        {"key": "3.11", "minor": "3.11", "freethreaded": False, "prerelease": False,
         "available": False, "reason": "not installed for this platform", "probe": {}},
    ]
    sweep.benchmarks = [
        {"id": "call_simple", "group": "micro", "description": "calls"},
        {"id": "threads_serial", "group": "threaded", "description": "serial"},
        {"id": "threads_parallel", "group": "threaded", "description": "parallel"},
    ]
    for (benchmark, key), median in TIMES.items():
        group = "threaded" if benchmark.startswith("threads_") else "micro"
        sweep.measurements.append(Measurement(
            interpreter=key, benchmark=benchmark, group=group, loops=100,
            values_ns=[median * 100], per_op_ns=[median], median_ns=median,
            min_ns=median, mean_ns=median, stddev_ns=0.0, status=STATUS_OK,
        ))
    return sweep


def render_table(sweep, baseline=None):
    stream = io.StringIO()
    table_report.render(sweep, baseline=baseline, stream=stream, colour=False)
    return stream.getvalue()


def test_table_shows_speedups_against_the_baseline():
    output = render_table(build_sweep())
    assert "2.00x" in output   # 3.14 is twice as fast as 3.10
    assert "2.50x" in output   # 3.15 is 2.5x
    assert "562" not in output


def test_table_marks_the_prerelease_column():
    assert "3.15*" in render_table(build_sweep())
    assert "pre-release" in render_table(build_sweep()).lower() or \
        "provisional" in render_table(build_sweep())


def test_table_reports_free_threading_against_its_own_twin():
    output = render_table(build_sweep())
    assert "free-threading cost" in output
    assert "3.14t/3.14" in output
    assert "0.80x" in output   # 125ns vs 100ns


def test_table_reports_thread_scaling():
    output = render_table(build_sweep())
    assert "thread scaling" in output
    assert "4.00x" in output   # free-threaded build scales across 4 threads


def test_table_lists_unavailable_interpreters():
    assert "3.11 unavailable" in render_table(build_sweep())


def test_table_honours_an_explicit_baseline():
    output = render_table(build_sweep(), baseline="3.14")
    assert "vs 3.14" in output


def test_table_falls_back_when_baseline_is_unknown():
    output = render_table(build_sweep(), baseline="3.99")
    assert "vs 3.10" in output


def test_table_marks_degraded_cells():
    sweep = build_sweep()
    for measurement in sweep.measurements:
        if measurement.interpreter == "3.14" and measurement.benchmark == "call_simple":
            measurement.status = STATUS_DEGRADED
            measurement.note = "cpu governor is 'ondemand'"
    output = render_table(sweep)
    assert "2.00x*" in output
    assert "ondemand" in output


def test_table_shows_a_dash_for_failed_measurements():
    sweep = build_sweep()
    sweep.measurements = [
        item for item in sweep.measurements
        if not (item.interpreter == "3.15" and item.benchmark == "call_simple")
    ]
    sweep.measurements.append(Measurement(
        interpreter="3.15", benchmark="call_simple", group="micro",
        status=STATUS_ERROR, note="driver produced no parsable result",
    ))
    output = render_table(sweep)
    assert "—" in output
    assert "failed" in output


def test_table_handles_a_sweep_with_no_interpreters():
    sweep = build_sweep()
    for item in sweep.interpreters:
        item["available"] = False
    assert "No available interpreters" in render_table(sweep)


def test_markdown_contains_every_section():
    text = markdown_report.render(build_sweep())
    for heading in ("# Python version speed benchmark", "## Environment",
                    "## Interpreters", "## Summary", "## Per-benchmark results",
                    "## Free-threading cost", "## Thread scaling", "## Caveats"):
        assert heading in text


def test_markdown_tables_have_matching_column_counts():
    text = markdown_report.render(build_sweep())
    for block in text.split("\n\n"):
        rows = [line for line in block.splitlines() if line.startswith("|")]
        if len(rows) < 2:
            continue
        widths = {row.count("|") for row in rows}
        assert len(widths) == 1, "ragged table:\n%s" % block


def test_markdown_flags_the_prerelease_and_the_missing_interpreter():
    text = markdown_report.render(build_sweep())
    assert "pre-release" in text
    assert "`3.11` was not benchmarked" in text


def test_markdown_reports_gil_state_for_freethreaded_builds():
    text = markdown_report.render(build_sweep())
    assert "free-threaded" in text
    assert "disabled" in text


def test_markdown_handles_a_sweep_with_no_interpreters():
    sweep = build_sweep()
    for item in sweep.interpreters:
        item["available"] = False
    assert "No available interpreters" in markdown_report.render(sweep)
