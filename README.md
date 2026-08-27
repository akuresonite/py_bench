# py_bench

Measure how much faster CPython has actually become, release by release, on **your**
machine — and what removing the GIL costs.

`pybench` downloads matching CPython builds for 3.10 → 3.15 (plus the free-threaded
no-GIL variants of 3.13/3.14/3.15), runs ~55 stdlib-only benchmarks across all of
them, and prints a comparison table.

```
benchmark                    3.10     3.11     3.12     3.13     3.14    3.15*
  micro
attr_access              132.9 ns    1.79x    1.81x    1.71x    2.23x    2.35x
call_simple              127.1 ns    1.33x    1.33x    1.36x    1.66x    1.84x
exception_raise          295.0 ns    1.20x    1.13x    1.05x    1.28x    1.34x
  mini
deepcopy_tree           108.46 us    1.36x    1.37x    1.40x    2.24x    2.46x
fib_recursive           239.54 us    1.59x    1.81x    1.94x    1.97x    2.03x
```

## Quickstart

The only prerequisite is [`uv`](https://docs.astral.sh/uv/getting-started/installation/),
which supplies the interpreters. Python itself is not a prerequisite — `uv` provides
that too.

```bash
git clone https://github.com/akuresonite/py_bench.git
cd py_bench

uv run pybench doctor     # is this machine fit to benchmark?
uv run pybench install    # fetch the nine interpreters (~2 GiB, once)
uv run pybench run        # sweep everything (~10-20 min)
```

Already have a Python 3.10+ on your PATH? `python -m pybench <command>` works
identically — the harness has no third-party dependencies.

Short on time or patience:

```bash
uv run pybench run --group micro --rounds 3            # micro only
uv run pybench run --only json --only regex            # just some benchmarks
uv run pybench run --minors 3.10,3.13 --no-freethreaded  # a smaller matrix
```

## Commands

| Command | What it does |
| --- | --- |
| `pybench doctor` | Reports CPU governor, thermals, throttling, power source and load, and explains what to fix. |
| `pybench install` | Downloads the interpreter matrix through `uv`. |
| `pybench list` | Shows each resolved build: version, GIL state, JIT state, path. |
| `pybench run` | Executes a sweep, writes `results/sweep-*.json`, prints the table, writes `reports/sweep-*.md`. |
| `pybench report` | Re-renders any past results file. `--baseline 3.12`, `--format markdown`. |

Useful `run` flags: `--repeats N` (repeat the whole matrix and aggregate),
`--pin 2,3` (pin to specific cores on Linux), `--baseline 3.12`,
`--min-time-ms`, `--warmup`, `--rounds`, `--allow-system`.

## Other Python implementations

CPython is not the only implementation, and the same benchmarks run against others:

```bash
uv run pybench run --with-rustpython              # RustPython, from PATH or ~/.cargo/bin
uv run pybench run --extra pypy=/usr/bin/pypy3    # any interpreter binary; repeatable
```

Build RustPython first if you do not have it:

```bash
cargo install --git https://github.com/RustPython/RustPython --locked rustpython
```

These are reported in their own **Other implementations** section rather than mixed
into the CPython version ladder, because a different implementation is not a different
version.

They also do not get a vote on which benchmarks run. The benchmark catalogue is the
set every *reference* (CPython) build can execute; an alternative implementation that
cannot run a benchmark leaves a dash in its own column and changes nothing for anyone
else. Without that rule, adding one incomplete implementation would silently delete
benchmarks from the entire comparison — which is precisely the failure mode you would
never notice in the output.

## What it measures

| Group | Count | Contents |
| --- | --- | --- |
| `startup` | 2 | Interpreter startup, bare and with common imports. Timed by spawning processes, since startup cannot be timed from inside. |
| `micro` | 36 | Calls, attribute access (with and without `__slots__`), dicts, lists, sets, strings and f-strings, integer and float arithmetic, comprehensions, generators, exceptions, sorting, name lookup. |
| `mini` | 14 | json, regex, pickle, deepcopy, nbody, spectral-norm, binary-trees, matrix multiply, recursive fib, asyncio fan-out. |
| `threaded` | 3 | The same CPU work run serially and across four threads, so the report can show real parallel speedup. |

## How the numbers are kept honest

**One interpreter source.** Every build comes from `uv`'s python-build-standalone
distributions — same toolchain, same optimisation configuration, same libc. Your
distro's `/usr/bin/python3` is never used, because comparing it to a PGO+LTO build
would measure packaging, not CPython.

**One benchmark source text.** Benchmark code is stdlib-only and 3.10-compatible, so
the identical file runs on every interpreter. No version gets a hand-tuned variant.

**Interleaved execution.** The runner iterates benchmark-major: benchmark A on all
nine interpreters, then benchmark B. A sweep takes tens of minutes and machines drift
thermally across that window; running all of 3.10 then all of 3.15 would charge that
drift to whichever version ran last and read as a regression.

**Fresh subprocess per measurement.** Nothing leaks between benchmarks — not caches,
not GC state, not interned strings. `PYTHONHASHSEED` is fixed so dict and set
benchmarks are reproducible.

**Calibrate, warm up, take the median.** Each benchmark grows its inner loop count
until one measurement takes at least 50 ms, discards warmup rounds, and reports the
median of what remains. Min, mean and standard deviation are kept in the JSON.

**Degraded runs are labelled, not hidden.** Before and after every measurement the
runner samples CPU temperature, frequency, load and — on a Raspberry Pi — the SoC
throttle bits. If the machine was throttling, running hot, heavily loaded, or on a
non-`performance` governor, that measurement is marked `degraded` in the results and
flagged with `*` in every report. A number you should not trust is never presented
as one you should.

For stable numbers on Linux, set the governor before a sweep:

```bash
sudo cpupower frequency-set -g performance
```

## Reading the output

- The baseline column (oldest version by default) is an absolute per-operation time.
  Every other column is a **speedup ratio** against it: `1.83x` means 83% faster.
- The **free-threading** table compares each no-GIL build against its own GIL twin
  (`3.14t` vs `3.14`), so that cost reads separately from the version ladder. Below
  `1.00x` means the free-threaded build is slower.
- **Thread scaling** divides serial by parallel wall time for identical work. GIL
  builds sit near `1.00x`; free-threaded builds should approach the core count.
- `*` on a version means a pre-release. `*` on a number means a degraded measurement.
  `—` means the measurement failed.

Results are JSON first: `results/sweep-*.json` holds every raw value, and the
reporters only read it. Re-render an old sweep at any time with `pybench report`.

## A worked example

[`examples/raspberry-pi-5.md`](examples/raspberry-pi-5.md) is a full sweep — 55
benchmarks, nine interpreters, 495 measurements, none degraded — from a Raspberry Pi 5
(4-core aarch64) with the governor pinned to `performance`. The raw
[`examples/raspberry-pi-5.json`](examples/raspberry-pi-5.json) is what the reporters
actually read.

Geometric mean speedup against 3.10:

| Group | 3.11 | 3.12 | 3.13 | 3.14 | 3.15a8 |
| --- | --- | --- | --- | --- | --- |
| startup | 0.99x | 0.96x | 0.88x | 0.86x | **0.87x** |
| micro | 1.25x | 1.20x | 1.19x | 1.36x | **1.42x** |
| mini | 1.26x | 1.34x | 1.38x | 1.36x | **1.45x** |

Three things that sweep showed, which are the sort of thing this tool exists to find:

- **Execution got substantially faster; startup got slower.** 3.15a8 runs micro
  benchmarks 1.42x faster than 3.10 and mini workloads 1.45x faster, but starts up
  about 13% *slower*. If your workload is short-lived scripts rather than long-running
  processes, the version ladder is not free.
- **Progress is not monotonic per benchmark.** `int_arith` and `local_lookup`
  regressed through 3.12 and 3.13 before 3.14 and 3.15 pulled ahead;
  `str_startswith` more than doubled at 3.13 and stayed there. A single geometric
  mean hides both.
- **Free-threading now costs much less than it did.** Single-threaded geometric mean
  against each build's own GIL twin: `3.13t` **0.77x**, `3.14t` **0.94x**, `3.15t`
  **0.89x**. Meanwhile the parallel benchmark scales 2.4-2.8x across four threads on
  the free-threaded builds while every GIL build sits at 0.97x — no scaling at all.
  Thread *creation*, though, is roughly 8x more expensive without the GIL.

## Caveats

- **3.15 is an alpha.** Its numbers are provisional and change between releases.
- **Free-threaded builds differ in build configuration**, not just in the GIL, so the
  comparison measures both together.
- **JIT.** On the current python-build-standalone builds the JIT is compiled in for
  3.13+ but disabled by default; `pybench list` reports what each build actually has.
- **One host, one story.** Results describe the machine that produced them.
- This is not a replacement for [`pyperformance`](https://github.com/python/pyperformance).
  It trades that suite's breadth for a sweep you can run in minutes.

## Development

```bash
uv run --with pytest -- python -m pytest tests -q
```

The suite covers the results schema, loop calibration, comparison arithmetic,
degraded-run detection, catalogue intersection and report rendering, and asserts that
every benchmark both runs and scales with its loop count. CI runs it on Linux, macOS
and Windows against 3.10 and 3.13, plus a two-version smoke sweep on each platform.

## Licence

MIT — see [LICENSE](LICENSE).
