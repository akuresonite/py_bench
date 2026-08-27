"""Loop calibration and benchmark discovery inside the driver."""

import _driver
import pytest


def test_calibrate_grows_until_target_is_met(monkeypatch):
    """Ten nanoseconds per loop; a 1 us target needs at least 100 loops."""
    monkeypatch.setattr(_driver, "_time_once", lambda call, loops: loops * 10)
    loops, elapsed = _driver.calibrate(lambda loops: None, min_time_ns=1000)
    assert loops >= 100
    assert elapsed >= 1000


def test_calibrate_returns_immediately_when_already_slow(monkeypatch):
    monkeypatch.setattr(_driver, "_time_once", lambda call, loops: 10 ** 9)
    loops, _ = _driver.calibrate(lambda loops: None, min_time_ns=1000)
    assert loops == 1


def test_calibrate_terminates_on_unmeasurable_work(monkeypatch):
    """A clock that always reads zero must not spin forever."""
    monkeypatch.setattr(_driver, "_time_once", lambda call, loops: 0)
    loops, _ = _driver.calibrate(lambda loops: None, min_time_ns=1000)
    assert loops >= _driver.MAX_LOOPS


def test_calibrate_never_exceeds_the_cap(monkeypatch):
    monkeypatch.setattr(_driver, "_time_once", lambda call, loops: 1)
    loops, _ = _driver.calibrate(lambda loops: None, min_time_ns=10 ** 12)
    assert loops <= _driver.MAX_LOOPS


def test_discovery_finds_benchmarks_in_every_group():
    found = _driver.discover()
    assert found
    groups = {value[3] for value in found.values()}
    assert {"micro", "mini", "threaded"} <= groups
    assert "__error__" not in "".join(found)


def test_discovered_benchmarks_have_descriptions():
    for bench_id, value in _driver.discover().items():
        assert value[4], "benchmark %s has no docstring" % bench_id


def test_measure_returns_consistent_statistics():
    result = _driver.measure("local_lookup", min_time_ms=1.0, warmup=0, rounds=3)
    assert result["benchmark"] == "local_lookup"
    assert result["loops"] > 0
    assert len(result["values_ns"]) == 3
    assert result["min_ns"] <= result["median_ns"]
    assert result["per_op_ns"][0] == pytest.approx(
        result["values_ns"][0] / result["loops"]
    )


def test_measure_rejects_unknown_benchmark():
    with pytest.raises(SystemExit):
        _driver.measure("no_such_benchmark", min_time_ms=1.0, warmup=0, rounds=1)


def test_probe_reports_gil_and_jit_keys():
    info = _driver.probe()
    assert info["implementation"] == "cpython"
    assert "freethreaded_build" in info
    assert set(info["jit"]) >= {"built", "available", "enabled", "source"}
