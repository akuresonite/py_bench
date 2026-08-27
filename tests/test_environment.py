"""Environment probing, throttle decoding and degraded-run detection."""

from pybench import environment
from pybench.environment import NA, OK, WARN, Sample, decode_throttled, is_degraded


def test_sticky_throttle_bits_are_not_current_problems():
    """0x50000 is 'happened since boot', which must not degrade every measurement."""
    current, sticky = decode_throttled("0x50000")
    assert current == []
    assert "under-voltage has occurred" in sticky
    assert "throttling has occurred" in sticky


def test_current_throttle_bits_are_reported_as_current():
    current, sticky = decode_throttled("0x4")
    assert current == ["currently throttled"]
    assert sticky == []


def test_healthy_and_unparsable_throttle_values():
    assert decode_throttled("0x0") == ([], [])
    assert decode_throttled(None) == ([], [])
    assert decode_throttled("not-a-number") == ([], [])


def test_sticky_bits_alone_do_not_degrade_a_measurement():
    reading = Sample(throttled="0x50000", temperature_c=45.0, load_1m=0.1)
    assert is_degraded(reading, reading, "performance") is None


def test_current_throttling_degrades_a_measurement():
    reading = Sample(throttled="0x4", temperature_c=45.0, load_1m=0.1)
    assert "throttling" in is_degraded(reading, reading, "performance")


def test_hot_cpu_degrades_a_measurement():
    reading = Sample(temperature_c=85.0, load_1m=0.1)
    assert "temperature" in is_degraded(reading, reading, "performance")


def test_non_performance_governor_degrades_a_measurement():
    reading = Sample(temperature_c=40.0, load_1m=0.1)
    assert "governor" in is_degraded(reading, reading, "ondemand")


def test_absent_governor_does_not_degrade(monkeypatch):
    """Platforms without a governor concept must not mark everything degraded."""
    reading = Sample(temperature_c=40.0, load_1m=0.1)
    assert is_degraded(reading, reading, None) is None


def test_high_load_degrades_a_measurement(monkeypatch):
    monkeypatch.setattr(environment.os, "cpu_count", lambda: 4)
    reading = Sample(temperature_c=40.0, load_1m=99.0)
    assert "load" in is_degraded(reading, reading, "performance")


def test_a_sample_with_nothing_available_is_not_degraded():
    """On macOS or Windows most probes return None; that is not a failure."""
    reading = Sample()
    assert is_degraded(reading, reading, None) is None


def test_sample_dict_omits_unavailable_readings():
    assert Sample(temperature_c=50.0).as_dict() == {"temperature_c": 50.0}


def test_host_info_has_the_keys_reporters_read():
    info = environment.host_info()
    for key in ("system", "machine", "cpu_count", "governor", "host_python"):
        assert key in info


def test_checks_return_known_statuses():
    results = environment.checks()
    assert results
    assert {check.status for check in results} <= {OK, WARN, NA}
    assert all(check.detail for check in results)


def test_pin_command_is_empty_without_a_request():
    assert environment.pin_command(None) == []
    assert environment.pin_command("") == []
