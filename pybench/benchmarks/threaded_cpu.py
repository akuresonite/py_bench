"""Multi-threaded CPU work.

Kept in its own group so it never distorts the single-threaded comparison. On GIL
builds the parallel benchmark is expected to track the serial baseline; on
free-threaded builds it should scale with the core count.

Both benchmarks perform exactly the same total amount of work, so their ratio is
the achieved parallel speedup for the interpreter under test.
"""

import threading

GROUP = "threaded"

THREADS = 4
WORK_UNIT = 20_000


def _cpu_kernel(iterations):
    total = 0
    for i in range(iterations):
        total = (total + i * i) % 1000003
    return total


def bench_threads_serial(loops):
    """The full workload on a single thread (parallel baseline)."""
    for _ in range(loops):
        for _ in range(THREADS):
            _cpu_kernel(WORK_UNIT)
    return loops


def bench_threads_parallel(loops):
    """The same workload split across four threads."""
    for _ in range(loops):
        workers = [
            threading.Thread(target=_cpu_kernel, args=(WORK_UNIT,))
            for _ in range(THREADS)
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
    return loops


def bench_threads_spawn_join(loops):
    """Thread creation and teardown cost, with no real work."""
    for _ in range(loops):
        worker = threading.Thread(target=_cpu_kernel, args=(1,))
        worker.start()
        worker.join()
    return loops
