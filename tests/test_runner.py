"""Benchmark selection, catalogue intersection and progress rendering."""

from pybench import runner
from pybench.interpreters import Interpreter
from pybench.results import STATUS_ERROR, STATUS_OK, Measurement
from pybench.runner import RunConfig, _progress_line, _select, build_catalogue

CATALOGUE = [
    {"id": "call_simple", "group": "micro", "description": "a"},
    {"id": "nbody", "group": "mini", "description": "b"},
    {"id": "threads_parallel", "group": "threaded", "description": "c"},
]


def test_selection_orders_startup_first_then_micro_mini_threaded():
    selected = _select(list(CATALOGUE) + [
        {"id": "startup_bare", "group": "startup", "description": "d"}
    ], RunConfig())
    assert [item["group"] for item in selected] == ["startup", "micro", "mini", "threaded"]


def test_group_filter_keeps_only_that_group():
    selected = _select(list(CATALOGUE), RunConfig(groups=["mini"]))
    assert [item["id"] for item in selected] == ["nbody"]


def test_only_filter_matches_a_substring_case_insensitively():
    selected = _select(list(CATALOGUE), RunConfig(only=["THREADS"]))
    assert [item["id"] for item in selected] == ["threads_parallel"]


def test_filters_combine():
    selected = _select(list(CATALOGUE), RunConfig(groups=["micro"], only=["call"]))
    assert [item["id"] for item in selected] == ["call_simple"]


def test_catalogue_keeps_only_benchmarks_shared_by_every_interpreter(monkeypatch):
    """A benchmark missing on one interpreter must not leave a hole in the table."""
    catalogues = {
        "/a": [CATALOGUE[0], CATALOGUE[1]],
        "/b": [CATALOGUE[0]],
    }
    monkeypatch.setattr(
        "pybench.interpreters.catalogue", lambda path: catalogues[path]
    )
    entries = [
        Interpreter(key="3.10", minor="3.10", request="3.10", path="/a", available=True),
        Interpreter(key="3.11", minor="3.11", request="3.11", path="/b", available=True),
    ]
    ids = [item["id"] for item in build_catalogue(entries, RunConfig())]
    assert "call_simple" in ids
    assert "nbody" not in ids


def test_catalogue_always_appends_the_startup_benchmarks(monkeypatch):
    monkeypatch.setattr("pybench.interpreters.catalogue", lambda path: [CATALOGUE[0]])
    entries = [
        Interpreter(key="3.10", minor="3.10", request="3.10", path="/a", available=True)
    ]
    ids = [item["id"] for item in build_catalogue(entries, RunConfig())]
    assert "startup_bare" in ids and "startup_imports" in ids


def test_unavailable_interpreters_are_ignored_by_the_catalogue(monkeypatch):
    monkeypatch.setattr("pybench.interpreters.catalogue", lambda path: [CATALOGUE[0]])
    entries = [
        Interpreter(key="3.10", minor="3.10", request="3.10", path="/a", available=True),
        Interpreter(key="3.99", minor="3.99", request="3.99", available=False),
    ]
    assert build_catalogue(entries, RunConfig())


def _measurement(key, median, status=STATUS_OK):
    return Measurement(
        interpreter=key, benchmark="call_simple", group="micro",
        median_ns=median, min_ns=median, mean_ns=median, stddev_ns=0.0,
        loops=10, values_ns=[median], per_op_ns=[median], status=status,
    )


def test_progress_line_names_the_fastest_interpreter():
    entries = [
        Interpreter(key="3.10", minor="3.10", request="3.10", available=True),
        Interpreter(key="3.14", minor="3.14", request="3.14", available=True),
    ]
    cells = {"3.10": _measurement("3.10", 200.0), "3.14": _measurement("3.14", 100.0)}
    line = _progress_line(1, 10, CATALOGUE[0], cells, entries)
    assert "2/2 ok" in line
    assert "fastest 3.14" in line
    assert "2.00x" in line


def test_progress_line_survives_a_failed_baseline():
    entries = [
        Interpreter(key="3.10", minor="3.10", request="3.10", available=True),
        Interpreter(key="3.14", minor="3.14", request="3.14", available=True),
    ]
    cells = {
        "3.10": _measurement("3.10", None, status=STATUS_ERROR),
        "3.14": _measurement("3.14", 100.0),
    }
    line = _progress_line(1, 10, CATALOGUE[0], cells, entries)
    assert "1/2 ok" in line
    assert "fastest 3.14" in line


def test_run_config_records_whether_pinning_actually_applied():
    assert RunConfig(pin=None).as_dict()["pin_applied"] is False


def test_child_env_fixes_the_hash_seed():
    env = runner._child_env(RunConfig())
    assert env["PYTHONHASHSEED"] == "0"
    assert "PYTHONPATH" not in env


def test_installed_python_parsing_survives_paths_with_spaces(monkeypatch):
    """Windows user directories routinely contain spaces."""
    import subprocess

    from pybench import interpreters

    listing = (
        "cpython-3.13.13-windows-x86_64-none    C:\\Users\\John Doe\\uv\\python313\\python.exe\n"
        "cpython-3.10.20-linux-aarch64-gnu      /home/a b/.local/bin/python3.10 -> /real/python3.10\n"
        "cpython-3.10.20-linux-aarch64-gnu      /home/a b/uv/python/cpython-3.10/bin/python3.10\n"
        "cpython-3.14.4+freethreaded-linux-aarch64-gnu  /home/a b/uv/python/3.14t/bin/python3.14t\n"
        "pypy-7.3-linux-aarch64-gnu             /usr/bin/pypy\n"
    )
    monkeypatch.setattr(interpreters, "uv_python_dir", lambda: "/home/a b/uv/python")
    monkeypatch.setattr(
        interpreters, "_uv",
        lambda args, timeout=0: subprocess.CompletedProcess(args, 0, listing, ""),
    )
    monkeypatch.setattr(interpreters.os.path, "exists", lambda path: True)

    found = interpreters.installed_pythons()
    by_path = {item.path: item for item in found}
    assert "C:\\Users\\John Doe\\uv\\python313\\python.exe" in by_path
    assert "/home/a b/uv/python/cpython-3.10/bin/python3.10" in by_path
    assert not any("->" in item.path for item in found), "symlink rows must be skipped"
    assert not any(item.path == "/usr/bin/pypy" for item in found), "pypy is not cpython"
    assert by_path["/home/a b/uv/python/3.14t/bin/python3.14t"].freethreaded
    assert by_path["/home/a b/uv/python/cpython-3.10/bin/python3.10"].managed
    assert not by_path["C:\\Users\\John Doe\\uv\\python313\\python.exe"].managed


def test_alternative_implementations_do_not_shrink_the_catalogue(monkeypatch):
    """RustPython failing a benchmark must not delete it for the CPython builds."""
    catalogues = {
        "/cpy310": [CATALOGUE[0], CATALOGUE[1]],
        "/cpy313": [CATALOGUE[0], CATALOGUE[1]],
        "/rustpython": [CATALOGUE[0]],          # cannot import the mini benchmark
    }
    monkeypatch.setattr(
        "pybench.interpreters.catalogue", lambda path: catalogues[path]
    )
    entries = [
        Interpreter(key="3.10", minor="3.10", request="3.10", path="/cpy310",
                    available=True),
        Interpreter(key="3.13", minor="3.13", request="3.13", path="/cpy313",
                    available=True),
        Interpreter(key="rustpython", minor="3.13", request="/rustpython",
                    path="/rustpython", available=True, source="path",
                    implementation="rustpython", reference=False),
    ]
    ids = [item["id"] for item in build_catalogue(entries, RunConfig())]
    assert "nbody" in ids, "an alternative implementation must not get a vote"
    assert "call_simple" in ids


def test_catalogue_falls_back_to_all_when_nothing_is_a_reference(monkeypatch):
    monkeypatch.setattr("pybench.interpreters.catalogue", lambda path: [CATALOGUE[0]])
    entries = [
        Interpreter(key="rustpython", minor="3.13", request="/r", path="/r",
                    available=True, source="path", reference=False)
    ]
    assert [item["id"] for item in build_catalogue(entries, RunConfig())
            if item["group"] != "startup"] == ["call_simple"]
