# Python version speed benchmark

Sweep `20260827T170633Z` — 2026-08-27T17:06:33+00:00

## Environment

| Property | Value |
| --- | --- |
| Machine | Raspberry Pi 5 Model B Rev 1.1 |
| Architecture | aarch64 |
| Cores | 4 |
| Memory | 7.87 GiB |
| System | Linux 6.18.34+rpt-rpi-2712 |
| CPU governor | performance |
| Protocol | 50 ms minimum, 2 warmup, 5 rounds, 1 repeat(s) |
| CPU pinning | not used |
| PYTHONHASHSEED | 0 |

## Interpreters

| Key | Version | Build | GIL | JIT | Source | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 3.10 | 3.10.20 | standard | enabled | not built | uv | ok |
| 3.11 | 3.11.15 | standard | enabled | not built | uv | ok |
| 3.12 | 3.12.13 | standard | enabled | not built | uv | ok |
| 3.13 | 3.13.13 | standard | enabled | built, disabled | uv | ok |
| 3.14 | 3.14.4 | standard | enabled | built, disabled | uv | ok |
| 3.15 | 3.15.0a8 | standard | enabled | built, disabled | uv | pre-release ⚠ |
| 3.13t | 3.13.13 | free-threaded | disabled | not built | uv | ok |
| 3.14t | 3.14.4 | free-threaded | disabled | not built | uv | ok |
| 3.15t | 3.15.0a8 | free-threaded | disabled | not built | uv | pre-release ⚠ |

## Summary

Geometric mean of per-benchmark speedup against `3.10`. Higher is faster.

| Group | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 ⚠ |
| --- | --- | --- | --- | --- | --- | --- |
| startup | 1.00x | 0.99x | 0.96x | 0.88x | 0.86x | 0.87x |
| micro | 1.00x | 1.25x | 1.20x | 1.19x | 1.36x | 1.42x |
| mini | 1.00x | 1.26x | 1.34x | 1.38x | 1.36x | 1.45x |
| threaded | 1.00x | 1.00x | 0.98x | 0.94x | 1.15x | 1.23x |

## Per-benchmark results

The `3.10` column is an absolute per-operation time; every other column is a speedup ratio against it.

### startup

| Benchmark | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 ⚠ |
| --- | --- | --- | --- | --- | --- | --- |
| `startup_bare` | 13.56 ms | 1.05x | 1.03x | 0.91x | 0.89x | 0.89x |
| `startup_imports` | 38.12 ms | 0.93x | 0.88x | 0.85x | 0.82x | 0.86x |

### micro

| Benchmark | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 ⚠ |
| --- | --- | --- | --- | --- | --- | --- |
| `attr_access` | 132.9 ns | 1.79x | 1.81x | 1.71x | 2.23x | 2.35x |
| `attr_property` | 143.5 ns | 1.23x | 1.50x | 1.55x | 2.01x | 2.09x |
| `attr_slots` | 110.6 ns | 1.67x | 1.54x | 1.47x | 1.91x | 2.03x |
| `call_builtin` | 84.0 ns | 1.30x | 1.22x | 1.13x | 1.52x | 1.61x |
| `call_kwargs` | 205.9 ns | 1.26x | 1.19x | 1.14x | 1.52x | 1.60x |
| `call_method` | 134.7 ns | 1.34x | 1.33x | 1.36x | 1.67x | 1.81x |
| `call_simple` | 127.1 ns | 1.33x | 1.33x | 1.36x | 1.66x | 1.84x |
| `call_star_args` | 133.3 ns | 1.22x | 1.25x | 1.18x | 1.44x | 1.48x |
| `dataclass_create` | 309.5 ns | 1.31x | 1.11x | 1.52x | 1.50x | 1.64x |
| `dict_build` | 231.1 ns | 1.10x | 0.98x | 0.93x | 1.04x | 1.13x |
| `dict_get_set` | 130.4 ns | 1.34x | 1.26x | 1.15x | 1.25x | 1.29x |
| `exception_raise` | 295.0 ns | 1.20x | 1.13x | 1.05x | 1.28x | 1.34x |
| `float_arith` | 95.2 ns | 1.16x | 1.20x | 1.13x | 1.13x | 1.30x |
| `generator_yield` | 91.8 ns | 1.17x | 1.34x | 1.36x | 1.55x | 1.65x |
| `global_lookup` | 72.9 ns | 1.29x | 1.21x | 1.10x | 1.53x | 1.67x |
| `instance_create` | 307.9 ns | 1.33x | 1.29x | 1.89x | 1.88x | 1.95x |
| `int_arith` | 115.0 ns | 1.07x | 0.95x | 0.85x | 1.24x | 1.36x |
| `int_bigint` | 306.8 ns | 1.11x | 0.94x | 0.88x | 1.03x | 1.02x |
| `isinstance_check` | 92.0 ns | 1.26x | 1.22x | 1.08x | 1.35x | 1.42x |
| `list_append` | 131.7 ns | 1.55x | 1.49x | 1.39x | 1.34x | 1.42x |
| `list_comprehension` | 1.72 us | 1.18x | 1.53x | 1.61x | 1.46x | 1.55x |
| `list_index` | 205.6 ns | 1.58x | 1.38x | 1.32x | 1.57x | 1.51x |
| `local_lookup` | 58.3 ns | 1.10x | 1.01x | 0.92x | 1.37x | 1.50x |
| `set_ops` | 242.5 ns | 1.57x | 1.57x | 1.52x | 1.65x | 1.52x |
| `sort_ints` | 13.12 us | 1.00x | 0.93x | 0.95x | 0.95x | 0.94x |
| `sort_key` | 25.14 us | 1.22x | 1.04x | 1.16x | 1.19x | 1.15x |
| `str_concat` | 144.8 ns | 1.50x | 1.37x | 1.25x | 1.34x | 1.44x |
| `str_encode_decode` | 395.2 ns | 1.11x | 1.03x | 1.01x | 1.07x | 1.07x |
| `str_format` | 552.2 ns | 1.06x | 0.97x | 0.98x | 0.94x | 1.01x |
| `str_fstring` | 583.0 ns | 1.02x | 1.04x | 1.02x | 0.91x | 0.99x |
| `str_join` | 158.3 ns | 1.08x | 1.08x | 1.01x | 1.12x | 1.06x |
| `str_methods` | 746.8 ns | 1.07x | 0.91x | 0.90x | 0.90x | 0.94x |
| `str_startswith` | 275.3 ns | 1.07x | 1.06x | 2.13x | 2.21x | 2.39x |
| `try_no_exception` | 68.6 ns | 1.20x | 1.07x | 0.93x | 1.10x | 1.09x |
| `unpack_sequence` | 147.6 ns | 1.31x | 1.38x | 1.11x | 1.39x | 1.56x |
| `while_loop` | 98.7 ns | 1.45x | 1.23x | 1.04x | 1.18x | 1.17x |

### mini

| Benchmark | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 ⚠ |
| --- | --- | --- | --- | --- | --- | --- |
| `asyncio_gather` | 467.64 us | 1.34x | 1.54x | 1.54x | 1.72x | 1.75x |
| `asyncio_sleep0` | 82.51 us | 1.26x | 1.39x | 1.55x | 1.49x | 1.51x |
| `binary_trees` | 129.08 us | 1.53x | 1.68x | 1.82x | 1.84x | 1.91x |
| `deepcopy_tree` | 108.46 us | 1.36x | 1.37x | 1.40x | 2.24x | 2.46x |
| `event_loop_startup` | 37.14 us | 1.28x | 1.34x | 1.39x | 1.27x | 1.27x |
| `fib_recursive` | 239.54 us | 1.59x | 1.81x | 1.94x | 1.97x | 2.03x |
| `json_dumps` | 25.46 us | 0.96x | 1.44x | 1.38x | 1.28x | 1.72x |
| `json_loads` | 16.57 us | 1.01x | 0.94x | 0.93x | 0.89x | 0.96x |
| `matrix_multiply` | 660.77 us | 1.26x | 1.35x | 1.39x | 1.13x | 1.17x |
| `nbody` | 10.99 us | 1.40x | 1.44x | 1.38x | 1.17x | 1.21x |
| `pickle_roundtrip` | 13.36 us | 1.01x | 0.94x | 0.89x | 0.90x | 0.88x |
| `regex_compile` | 99.89 us | 1.36x | 1.39x | 1.53x | 1.47x | 1.54x |
| `regex_search` | 75.63 us | 1.09x | 0.97x | 1.02x | 0.94x | 0.95x |
| `spectral_norm` | 197.76 us | 1.44x | 1.57x | 1.53x | 1.53x | 1.87x |

### threaded

| Benchmark | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 ⚠ |
| --- | --- | --- | --- | --- | --- | --- |
| `threads_parallel` | 9.52 ms | 1.07x | 0.99x | 0.90x | 1.24x | 1.39x |
| `threads_serial` | 9.24 ms | 1.07x | 0.99x | 0.86x | 1.25x | 1.39x |
| `threads_spawn_join` | 45.57 us | 0.89x | 0.97x | 1.07x | 0.98x | 0.98x |

## Free-threading cost

Each free-threaded build against its own GIL twin. Below `1.00x` means the free-threaded build is slower at that benchmark.

| Benchmark | 3.13t / 3.13 | 3.14t / 3.14 | 3.15t / 3.15 |
| --- | --- | --- | --- |
| `startup_bare` | 0.74x | 0.73x | 0.74x |
| `startup_imports` | 0.69x | 0.78x | 0.78x |
| `attr_access` | 0.55x | 0.75x | 0.67x |
| `attr_property` | 0.58x | 0.99x | 0.95x |
| `attr_slots` | 0.53x | 0.73x | 0.67x |
| `call_builtin` | 0.86x | 1.03x | 0.95x |
| `call_kwargs` | 0.93x | 0.93x | 0.88x |
| `call_method` | 0.88x | 1.00x | 0.93x |
| `call_simple` | 0.88x | 1.03x | 0.93x |
| `call_star_args` | 0.91x | 1.03x | 0.95x |
| `dataclass_create` | 0.58x | 0.73x | 0.70x |
| `dict_build` | 0.90x | 1.00x | 0.91x |
| `dict_get_set` | 0.73x | 0.85x | 0.82x |
| `exception_raise` | 1.00x | 0.84x | 0.82x |
| `float_arith` | 0.82x | 0.90x | 0.91x |
| `generator_yield` | 0.75x | 0.97x | 0.89x |
| `global_lookup` | 0.86x | 1.02x | 0.90x |
| `instance_create` | 0.47x | 0.82x | 0.76x |
| `int_arith` | 1.03x | 0.99x | 0.87x |
| `int_bigint` | 1.15x | 1.05x | 0.99x |
| `isinstance_check` | 0.85x | 1.02x | 0.94x |
| `list_append` | 0.63x | 0.84x | 0.86x |
| `list_comprehension` | 0.72x | 0.94x | 0.85x |
| `list_index` | 0.81x | 0.89x | 0.86x |
| `local_lookup` | 0.98x | 1.02x | 0.90x |
| `set_ops` | 0.65x | 0.74x | 0.78x |
| `sort_ints` | 1.00x | 0.99x | 1.00x |
| `sort_key` | 0.85x | 0.91x | 0.95x |
| `str_concat` | 0.72x | 1.06x | 1.00x |
| `str_encode_decode` | 0.97x | 1.08x | 1.04x |
| `str_format` | 0.97x | 1.03x | 0.93x |
| `str_fstring` | 1.03x | 1.09x | 1.03x |
| `str_join` | 0.87x | 0.89x | 0.92x |
| `str_methods` | 1.05x | 1.09x | 1.05x |
| `str_startswith` | 0.72x | 1.05x | 0.98x |
| `try_no_exception` | 1.05x | 1.11x | 0.97x |
| `unpack_sequence` | 0.68x | 1.05x | 0.94x |
| `while_loop` | 0.90x | 1.09x | 1.01x |
| `asyncio_gather` | 0.57x | 0.82x | 0.80x |
| `asyncio_sleep0` | 0.65x | 0.94x | 0.93x |
| `binary_trees` | 0.59x | 0.99x | 1.00x |
| `deepcopy_tree` | 0.63x | 0.87x | 0.92x |
| `event_loop_startup` | 0.68x | 0.94x | 0.87x |
| `fib_recursive` | 0.61x | 0.95x | 0.97x |
| `json_dumps` | 0.88x | 0.99x | 0.89x |
| `json_loads` | 0.84x | 0.88x | 0.84x |
| `matrix_multiply` | 0.50x | 0.96x | 0.85x |
| `nbody` | 0.52x | 0.83x | 0.82x |
| `pickle_roundtrip` | 0.85x | 0.88x | 0.89x |
| `regex_compile` | 0.59x | 0.89x | 0.85x |
| `regex_search` | 1.05x | 1.07x | 1.06x |
| `spectral_norm` | 0.71x | 0.95x | 0.94x |
| `threads_parallel` | 2.36x | 1.86x | 2.53x |
| `threads_serial` | 1.00x | 0.99x | 0.87x |
| `threads_spawn_join` | 0.13x | 0.12x | 0.09x |
| **geometric mean** | **0.77x** | **0.94x** | **0.89x** |

## Thread scaling

Identical CPU work run serially and across four threads. The ratio is the achieved parallel speedup; GIL builds are expected near `1.00x`.

| Interpreter | Parallel speedup |
| --- | --- |
| 3.10 | 0.97x |
| 3.11 | 0.97x |
| 3.12 | 0.98x |
| 3.13 | 1.01x |
| 3.14 | 0.97x |
| 3.15 ⚠ | 0.97x |
| 3.13t | 2.38x |
| 3.14t | 1.82x |
| 3.15t ⚠ | 2.82x |

## Caveats

- ⚠ 3.15, 3.15t are pre-release builds; the numbers are provisional and may change before final release.
- Free-threaded builds differ from their GIL twins in build configuration as well as in the GIL, so the comparison measures both.
- Results describe the machine that produced them and do not transfer to other hardware.

