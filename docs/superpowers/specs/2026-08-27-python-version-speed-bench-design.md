# Python Version Speed Bench — Design

**Date:** 2026-08-27
**Status:** Approved

## Purpose

Measure and compare CPython execution speed across versions 3.10 → 3.15, plus the
free-threaded (no-GIL) variants of 3.13/3.14/3.15, on a single machine. The output
answers two questions: *how much faster has CPython become, release over release*,
and *what does removing the GIL cost single-threaded code*.

The harness is a public, cloneable repository that runs on any platform `uv`
supports — Linux, macOS, Windows, on x86-64 or arm64. Nothing is Raspberry Pi
specific; Pi-only measurements (SoC throttle bits, core temperature) are treated as
optional environment probes that degrade to "not available" elsewhere.

## Non-goals

- Not a replacement for `pyperformance`. The suite here is curated for speed of
  iteration (minutes, not hours) and for showing *where* the interpreter changed.
- Not a cross-machine benchmark database. One sweep describes one host.
- No third-party dependencies in benchmark code, and none required to run a sweep.

## Fairness constraints

These are the constraints that make the numbers comparable at all:

1. **One interpreter source.** All builds come from `uv`'s python-build-standalone
   distributions, never the system or distro Python. Same toolchain, same PGO/LTO
   configuration, same libc across the matrix, so a delta is a CPython delta and not
   a packaging delta. A `--allow-system` escape hatch exists for hosts where `uv`
   cannot provide a version, and any sweep using it is marked as mixed-source.
2. **One benchmark source text.** Benchmark code is stdlib-only and written in
   3.10-compatible syntax — no PEP 695 generics, no `type` statements, no
   3.12+ f-string nesting. The identical file runs on every interpreter, so no
   version gets a hand-tuned variant.
3. **Interleaved execution.** The runner iterates benchmark-major, not
   interpreter-major: benchmark A on all interpreters, then benchmark B. A sweep
   takes tens of minutes and machines drift thermally over that window; blocked
   execution would charge that drift entirely to whichever version ran last and read
   as a regression.
4. **Degraded runs are labelled, never silently reported.** If the environment probe
   detects thermal throttling, a non-performance CPU governor, battery power, or high
   load, affected measurements carry `status: "degraded"` into the results file and
   are flagged in every report.

## Architecture

```
pybench/            harness package, runs on the host interpreter
  cli.py            install | list | doctor | run | report
  interpreters.py   matrix definition, uv installation, per-build metadata probe
  runner.py         sweep orchestration, subprocess per measurement
  environment.py    portable host/capability probing
  results.py        results schema, load/save, aggregation
  report/table.py   terminal comparison table
  report/markdown.py  markdown report
benchmarks/         stdlib-only, 3.10-safe benchmark modules
  _driver.py        timing driver; runs *inside* each target interpreter
results/            one JSON file per sweep — the durable artifact
reports/            generated markdown
tests/              pytest suite for the harness
```

### Interpreter matrix

Nine entries: standard builds of 3.10–3.15, plus free-threaded builds of 3.13, 3.14
and 3.15. Availability is resolved per platform at install time; entries `uv` cannot
supply on the current host are recorded as unavailable and skipped rather than
failing the sweep.

Each build is probed once by executing a small script inside it, capturing: full
version string, whether `Py_GIL_DISABLED` was set at build time, whether the GIL is
enabled at runtime (`sys._is_gil_enabled()`), and JIT status. JIT is reported as
`built` / `available` / `enabled` from `sys._jit` where it exists (3.14+) and from
`PY_CORE_CFLAGS` inspection on 3.13. If the distributions carry no JIT-enabled build
for the host platform, the honest report is "not built with JIT" across the board.

### Measurement protocol

- **Fresh subprocess per (interpreter × benchmark).** No contamination of caches, GC
  state, or interned strings between benchmarks.
- **Calibration.** The driver doubles the inner loop count until one measurement
  takes at least `--min-time-ms` (default 50 ms), so fast operations are not measured
  against clock resolution.
- **Warmup then measure.** Warmup rounds are discarded; the remaining rounds are
  recorded in full. The reported headline is the **median** — robust against
  scheduler jitter — with min, mean and stddev retained in the results file.
- **Startup is measured externally.** Interpreter startup cannot be timed from
  inside the interpreter, so the runner times `python -c pass` and
  `python -c "import json, re, ..."` subprocess spawns directly.
- **Optional CPU pinning** via `taskset` where present, recorded in the results file
  when used and reported as unavailable elsewhere.

### Benchmark set (~28, three groups)

- **micro** — startup (bare, with imports), simple/keyword/method calls, attribute
  access with and without `__slots__`, dict and list hot paths, f-strings, string
  methods, integer and float arithmetic, comprehensions, generators, exception
  raise/catch and zero-cost `try` (the 3.11 story), sorting, sequence unpacking,
  global vs. local lookup, `isinstance`, dataclass construction.
- **mini** — json round-trip, regex over a corpus, nbody, spectral-norm, pickle
  round-trip, `asyncio.gather` fan-out, deepcopy of a nested tree, binary-trees
  (allocation and GC pressure).
- **threaded** — CPU work across four threads, kept in its own group so it never
  distorts the single-threaded comparison. This is the group where free-threaded
  builds should diverge sharply from GIL builds.

### Results schema

A sweep writes one JSON document: schema version, sweep id, host description,
run configuration, the resolved interpreter list with probe metadata, the benchmark
catalogue, and a flat list of measurements. Each measurement carries interpreter key,
benchmark id, round index, loop count, raw nanosecond values, derived statistics,
status, and the environment sample taken alongside it. The JSON is the contract:
reporters read it and never re-measure.

### Reporting

`pybench report` prints a terminal table of per-benchmark medians with a ratio
against a chosen baseline (default 3.10) and writes the same tables to markdown.
Free-threaded builds are compared against their own GIL twin — "3.14t vs 3.14" — so
the free-threading cost reads separately from the version ladder.

## Testing

Pytest covers the harness: results schema round-trip, loop calibration, comparison
and ratio arithmetic, degraded-run detection, interpreter matrix resolution, markdown
rendering, and a smoke test that every benchmark module executes on the host
interpreter at tiny loop counts.

## Known caveats

- **3.15 is an alpha.** Its numbers are provisional and are labelled as such in every
  report.
- **Free-threaded builds are a different build configuration**, not just a runtime
  switch. Comparing 3.14t to 3.14 measures the combined cost of the build
  configuration and the disabled GIL.
- **One host, one story.** Results are valid for the machine that produced them.
