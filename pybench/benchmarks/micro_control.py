"""Arithmetic, control flow, exceptions, name lookup."""

GROUP = "micro"

_GLOBAL_VALUE = 1


def bench_int_arith(loops):
    """Small-integer arithmetic chain."""
    total = 0
    for i in range(loops):
        total = (total + i) * 3 % 1000003
    return total


def bench_int_bigint(loops):
    """Arbitrary-precision integer arithmetic."""
    base = 2 ** 200 + 1
    total = 0
    for i in range(loops):
        total = (base * (i + 1)) % (base - 3)
    return total


def bench_float_arith(loops):
    """Floating point arithmetic chain."""
    total = 1.0
    for i in range(loops):
        total = (total + i) * 0.5
        if total > 1e12:
            total = 1.0
    return total


def bench_generator_yield(loops):
    """Drive a generator to exhaustion."""

    def produce(count):
        for value in range(count):
            yield value

    total = 0
    remaining = loops
    while remaining > 0:
        chunk = 64 if remaining > 64 else remaining
        for value in produce(chunk):
            total += value
        remaining -= chunk
    return total


def bench_exception_raise(loops):
    """Raise and catch an exception."""
    total = 0
    for _ in range(loops):
        try:
            raise ValueError("benchmark")
        except ValueError:
            total += 1
    return total


def bench_try_no_exception(loops):
    """Enter and leave a try block that never raises (zero-cost try)."""
    total = 0
    for i in range(loops):
        try:
            total += i
        except ValueError:
            total -= 1
    return total


def bench_global_lookup(loops):
    """Repeated global name lookup."""
    total = 0
    for _ in range(loops):
        total += _GLOBAL_VALUE
    return total


def bench_local_lookup(loops):
    """Repeated local name lookup."""
    local_value = 1
    total = 0
    for _ in range(loops):
        total += local_value
    return total


def bench_while_loop(loops):
    """Bare while loop with a comparison."""
    i = 0
    total = 0
    while i < loops:
        total += i
        i += 1
    return total
