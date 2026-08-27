"""Schema, aggregation and comparison arithmetic."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pybench.results import (  # noqa: E402
    SCHEMA_VERSION,
    STATUS_DEGRADED,
    STATUS_ERROR,
    STATUS_OK,
    Cell,
    Measurement,
    Sweep,
    format_duration,
    geometric_mean,
    speedup,
)


def make_sweep():
    sweep = Sweep.new(host={"model": "test"}, config={"rounds": 3})
    sweep.interpreters = [
        {"key": "3.10", "minor": "3.10", "freethreaded": False, "prerelease": False,
         "available": True, "probe": {}},
        {"key": "3.14", "minor": "3.14", "freethreaded": False, "prerelease": False,
         "available": True, "probe": {}},
        {"key": "3.14t", "minor": "3.14", "freethreaded": True, "prerelease": False,
         "available": True, "probe": {}},
    ]
    sweep.benchmarks = [{"id": "call_simple", "group": "micro", "description": ""}]
    return sweep


def add(sweep, interpreter, median, repeat=0, status=STATUS_OK, note=None):
    sweep.measurements.append(Measurement(
        interpreter=interpreter, benchmark="call_simple", group="micro",
        repeat=repeat, loops=100, values_ns=[median * 100],
        per_op_ns=[median], median_ns=median, min_ns=median,
        mean_ns=median, stddev_ns=0.0, status=status, note=note,
    ))


def test_roundtrip_preserves_measurements(tmp_path):
    sweep = make_sweep()
    add(sweep, "3.10", 100.0)
    path = sweep.save(str(tmp_path / "sweep.json"))
    reloaded = Sweep.load(path)
    assert reloaded.sweep_id == sweep.sweep_id
    assert len(reloaded.measurements) == 1
    assert reloaded.measurements[0].median_ns == 100.0
    assert reloaded.cell("call_simple", "3.10").median_ns == 100.0


def test_load_rejects_unknown_schema(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema": SCHEMA_VERSION + 99, "sweep_id": "x",
                                "created_at": "now"}))
    with pytest.raises(ValueError, match="unsupported results schema"):
        Sweep.load(str(path))


def test_cell_aggregates_repeats_with_median():
    sweep = make_sweep()
    for index, value in enumerate([100.0, 300.0, 200.0]):
        add(sweep, "3.10", value, repeat=index)
    cell = sweep.cell("call_simple", "3.10")
    assert cell.median_ns == 200.0
    assert cell.min_ns == 100.0
    assert cell.repeats == 3
    assert cell.status == STATUS_OK


def test_cell_is_degraded_when_any_repeat_is():
    sweep = make_sweep()
    add(sweep, "3.10", 100.0, repeat=0)
    add(sweep, "3.10", 110.0, repeat=1, status=STATUS_DEGRADED, note="hot")
    cell = sweep.cell("call_simple", "3.10")
    assert cell.status == STATUS_DEGRADED
    assert cell.note == "hot"


def test_cell_with_only_errors_is_unusable():
    sweep = make_sweep()
    sweep.measurements.append(Measurement(
        interpreter="3.10", benchmark="call_simple", group="micro",
        status=STATUS_ERROR, note="boom",
    ))
    cell = sweep.cell("call_simple", "3.10")
    assert not cell.ok
    assert cell.note == "boom"


def test_errors_do_not_drag_down_a_good_repeat():
    sweep = make_sweep()
    add(sweep, "3.10", 100.0, repeat=0)
    sweep.measurements.append(Measurement(
        interpreter="3.10", benchmark="call_simple", group="micro",
        repeat=1, status=STATUS_ERROR, note="boom",
    ))
    cell = sweep.cell("call_simple", "3.10")
    assert cell.ok
    assert cell.median_ns == 100.0
    assert cell.repeats == 1


def test_speedup_is_baseline_over_candidate():
    faster = speedup(Cell(median_ns=200.0, status=STATUS_OK),
                     Cell(median_ns=100.0, status=STATUS_OK))
    assert faster == 2.0
    slower = speedup(Cell(median_ns=100.0, status=STATUS_OK),
                     Cell(median_ns=200.0, status=STATUS_OK))
    assert slower == 0.5


def test_speedup_is_none_when_either_side_missing():
    good = Cell(median_ns=100.0, status=STATUS_OK)
    missing = Cell(status=STATUS_ERROR)
    assert speedup(good, missing) is None
    assert speedup(missing, good) is None


def test_geometric_mean_of_reciprocals_is_one():
    assert geometric_mean([0.5, 2.0]) == pytest.approx(1.0)
    assert geometric_mean([2.0, 8.0]) == pytest.approx(4.0)


def test_geometric_mean_ignores_unusable_values():
    assert geometric_mean([2.0, 0.0, None, -1.0]) == pytest.approx(2.0)
    assert geometric_mean([]) is None


def test_missing_interpreter_lookup_returns_none():
    assert make_sweep().interpreter("3.99") is None


@pytest.mark.parametrize("value,expected", [
    (None, "—"), (562.8, "562.8 ns"), (19404.0, "19.40 us"),
    (7.5e6, "7.50 ms"), (2.5e9, "2.50 s"),
])
def test_format_duration_picks_a_unit(value, expected):
    assert format_duration(value) == expected
