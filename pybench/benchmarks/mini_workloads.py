"""Small realistic workloads built only from the standard library."""

import copy
import json
import pickle
import re

GROUP = "mini"


def _document():
    return {
        "id": 90210,
        "name": "benchmark-document",
        "tags": ["alpha", "beta", "gamma", "delta"],
        "active": True,
        "score": 3.14159,
        "nested": {
            "items": [
                {"key": "k%d" % i, "value": i, "flag": bool(i % 2)}
                for i in range(24)
            ],
            "meta": {"version": 3, "notes": None},
        },
    }


def setup_json_dumps():
    return _document()


def bench_json_dumps(loops, state):
    """Serialise a nested document to JSON."""
    document = state
    dumps = json.dumps
    out = None
    for _ in range(loops):
        out = dumps(document)
    return out


def setup_json_loads():
    return json.dumps(_document())


def bench_json_loads(loops, state):
    """Parse a nested JSON document."""
    text = state
    parse = json.loads
    out = None
    for _ in range(loops):
        out = parse(text)
    return out


def setup_regex_search():
    corpus = (
        "2026-08-27 21:04:11 INFO  worker=17 latency=142ms status=200 path=/api/v1/items\n"
        "2026-08-27 21:04:12 WARN  worker=03 latency=982ms status=503 path=/api/v1/search\n"
        "2026-08-27 21:04:13 ERROR worker=11 latency=  1ms status=500 path=/api/v1/items\n"
    ) * 24
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) (\w+)\s+worker=(\d+)"
                         r" latency=\s*(\d+)ms status=(\d+) path=(\S+)")
    return corpus, pattern


def bench_regex_search(loops, state):
    """Scan a log corpus with a compiled regex."""
    corpus, pattern = state
    total = 0
    for _ in range(loops):
        total += len(pattern.findall(corpus))
    return total


def bench_regex_compile(loops):
    """Compile a regex, defeating the internal pattern cache."""
    compile_re = re.compile
    out = None
    for i in range(loops):
        out = compile_re(r"^(?P<a%d>\w+)-(?P<b>\d+)\s*(?:[a-z]+)?$" % i)
    return out


def setup_pickle_roundtrip():
    return _document()


def bench_pickle_roundtrip(loops, state):
    """Pickle and unpickle a nested document."""
    document = state
    dumps = pickle.dumps
    loads = pickle.loads
    out = None
    for _ in range(loops):
        out = loads(dumps(document, protocol=pickle.HIGHEST_PROTOCOL))
    return out


def setup_deepcopy_tree():
    return _document()


def bench_deepcopy_tree(loops, state):
    """Deep-copy a nested structure."""
    document = state
    deepcopy = copy.deepcopy
    out = None
    for _ in range(loops):
        out = deepcopy(document)
    return out
