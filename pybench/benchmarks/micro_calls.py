"""Function and method call overhead."""

GROUP = "micro"


def _plain(a, b):
    return a + b


def _defaults(a, b=1, c=2, d=3):
    return a + b + c + d


class _Target(object):
    def method(self, a, b):
        return a + b

    @staticmethod
    def static(a, b):
        return a + b


def bench_call_simple(loops):
    """Positional call to a plain Python function."""
    func = _plain
    total = 0
    for _ in range(loops):
        total = func(total, 1)
    return total


def bench_call_kwargs(loops):
    """Call with keyword arguments and defaults."""
    func = _defaults
    total = 0
    for _ in range(loops):
        total = func(total, c=4, d=5)
    return total


def setup_call_method():
    return _Target()


def bench_call_method(loops, state):
    """Bound method call."""
    method = state.method
    total = 0
    for _ in range(loops):
        total = method(total, 1)
    return total


def bench_call_builtin(loops):
    """Call into a C builtin."""
    func = len
    data = (1, 2, 3, 4, 5)
    total = 0
    for _ in range(loops):
        total += func(data)
    return total


def bench_call_star_args(loops):
    """Call through *args unpacking."""
    func = _plain
    args = (1, 2)
    total = 0
    for _ in range(loops):
        total += func(*args)
    return total
