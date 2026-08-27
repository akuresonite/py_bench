"""Dict, list, tuple and sorting hot paths."""

GROUP = "micro"


def setup_dict_get_set():
    return {"alpha": 1, "beta": 2, "gamma": 3, "delta": 4}


def bench_dict_get_set(loops, state):
    """String-keyed dict read and write."""
    data = state
    total = 0
    for _ in range(loops):
        data["alpha"] = total
        total = data["alpha"] + data["beta"]
    return total


def bench_dict_build(loops):
    """Build a small dict from scratch."""
    data = None
    for i in range(loops):
        data = {"a": i, "b": i + 1, "c": i + 2, "d": i + 3}
    return data


def bench_list_append(loops):
    """Append into a list, flushing periodically to bound memory."""
    data = []
    append = data.append
    for i in range(loops):
        append(i)
        if len(data) >= 1024:
            del data[:]
    return len(data)


def bench_list_index(loops):
    """Indexed reads and writes on a list."""
    data = list(range(64))
    total = 0
    for i in range(loops):
        data[i & 63] = i
        total += data[(i + 1) & 63]
    return total


def bench_list_comprehension(loops):
    """List comprehension over a small range."""
    result = None
    for _ in range(loops):
        result = [x * 2 for x in range(32)]
    return result


def bench_unpack_sequence(loops):
    """Tuple unpacking."""
    data = (1, 2, 3, 4, 5)
    total = 0
    for _ in range(loops):
        a, b, c, d, e = data
        total += a + b + c + d + e
    return total


def setup_sort_ints():
    import random

    rng = random.Random(1234)
    return [rng.randrange(1_000_000) for _ in range(256)]


def bench_sort_ints(loops, state):
    """Sort a shuffled integer list."""
    source = state
    result = None
    for _ in range(loops):
        result = sorted(source)
    return result


def setup_sort_key():
    import random

    rng = random.Random(4321)
    return [(rng.randrange(1000), "item%d" % i) for i in range(256)]


def bench_sort_key(loops, state):
    """Sort with a key function."""
    source = state
    result = None
    for _ in range(loops):
        result = sorted(source, key=lambda pair: pair[1])
    return result


def bench_set_ops(loops):
    """Set membership and mutation."""
    data = set(range(64))
    total = 0
    for i in range(loops):
        if (i & 63) in data:
            total += 1
        data.add(i & 127)
        data.discard(i & 127)
    return total
