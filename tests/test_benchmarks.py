"""Every benchmark must execute on the host interpreter."""

import _driver
import pytest

FOUND = _driver.discover()


@pytest.mark.parametrize("bench_id", sorted(FOUND))
def test_benchmark_runs_at_tiny_loop_count(bench_id):
    _filename, func, setup, _group, _doc = FOUND[bench_id]
    call, _state = _driver._make_call(func, setup)
    call(2)


@pytest.mark.parametrize("bench_id", sorted(FOUND))
def test_benchmark_scales_with_loop_count(bench_id):
    """A benchmark whose work does not grow with `loops` cannot be calibrated."""
    if bench_id.startswith("threads_") or bench_id.startswith("asyncio_"):
        pytest.skip("scheduling noise dominates at tiny loop counts")
    _filename, func, setup, _group, _doc = FOUND[bench_id]
    call, _state = _driver._make_call(func, setup)
    call(50)  # warm the code path before comparing
    small = min(_driver._time_once(call, 50) for _ in range(5))
    large = min(_driver._time_once(call, 500) for _ in range(5))
    assert large > small * 2, "%s does not scale with loops" % bench_id
