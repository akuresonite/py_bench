"""Every benchmark must execute on the host interpreter."""

import _driver
import pytest

FOUND = _driver.discover()

#: Each measurement pays a fixed cost (a gc.collect plus timer overhead). Compare at a
#: loop count where the benchmark's own work dominates that, or the comparison below
#: measures the overhead instead of the benchmark.
SCALE_TARGET_NS = 5_000_000


@pytest.mark.parametrize("bench_id", sorted(FOUND))
def test_benchmark_runs_at_tiny_loop_count(bench_id):
    _filename, func, setup, _group, _doc = FOUND[bench_id]
    call, _state = _driver._make_call(func, setup)
    call(2)


@pytest.mark.parametrize("bench_id", sorted(FOUND))
def test_benchmark_scales_with_loop_count(bench_id):
    """A benchmark whose work does not grow with `loops` cannot be calibrated."""
    _filename, func, setup, group, _doc = FOUND[bench_id]
    if group == "threaded":
        pytest.skip("thread scheduling noise dominates on shared runners")
    call, _state = _driver._make_call(func, setup)

    base, _ = _driver.calibrate(call, SCALE_TARGET_NS)
    small = min(_driver._time_once(call, base) for _ in range(3))
    large = min(_driver._time_once(call, base * 10) for _ in range(3))

    # Ten times the loops should take roughly ten times as long; a benchmark doing
    # constant work would sit near 1x, so 5x discriminates with plenty of headroom.
    assert large > small * 5, (
        "%s does not scale with loops (%d loops: %d ns, %d loops: %d ns)"
        % (bench_id, base, small, base * 10, large)
    )
