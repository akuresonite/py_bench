"""asyncio scheduling throughput."""

import asyncio

GROUP = "mini"

_TASK_COUNT = 64


async def _noop(value):
    return value


async def _gather_round():
    return await asyncio.gather(*[_noop(i) for i in range(_TASK_COUNT)])


async def _chain(depth):
    if depth <= 0:
        return 0
    await asyncio.sleep(0)
    return 1 + await _chain(depth - 1)


async def _gather_body(loops):
    for _ in range(loops):
        await _gather_round()


async def _sleep_body(loops):
    for _ in range(loops):
        await _chain(16)


def bench_asyncio_gather(loops):
    """Fan out coroutines with asyncio.gather and collect the results."""
    asyncio.run(_gather_body(loops))
    return loops


def bench_asyncio_sleep0(loops):
    """Yield to the event loop repeatedly via sleep(0)."""
    asyncio.run(_sleep_body(loops))
    return loops


def bench_event_loop_startup(loops):
    """Create and tear down an event loop."""
    for _ in range(loops):
        loop = asyncio.new_event_loop()
        loop.close()
    return loops
