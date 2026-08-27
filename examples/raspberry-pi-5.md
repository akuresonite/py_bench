# Python version speed benchmark

Sweep `20260827T194703Z` — 2026-08-27T19:47:03+00:00

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
| rustpython | 3.14.0.alpha | free-threaded | disabled | not built | path | ok |

## Summary

Geometric mean of per-benchmark speedup against `3.10`. Higher is faster.

| Group | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 ⚠ |
| --- | --- | --- | --- | --- | --- | --- |
| startup | 1.00x | 1.00x | 0.91x | 0.88x | 0.85x | 0.88x |
| micro | 1.00x | 1.22x | 1.20x | 1.22x | 1.36x | 1.42x |
| mini | 1.00x | 1.26x | 1.34x | 1.38x | 1.36x | 1.45x |
| threaded | 1.00x | 1.03x | 0.99x | 0.96x | 1.16x | 1.25x |

## Per-benchmark results

The `3.10` column is an absolute per-operation time; every other column is a speedup ratio against it.

### startup

| Benchmark | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 ⚠ |
| --- | --- | --- | --- | --- | --- | --- |
| `startup_bare` | 13.34 ms | 1.05x | 0.90x | 0.90x | 0.86x | 0.88x |
| `startup_imports` | 38.95 ms | 0.96x | 0.91x | 0.86x | 0.84x | 0.89x |

### micro

| Benchmark | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 ⚠ |
| --- | --- | --- | --- | --- | --- | --- |
| `attr_access` | 121.2 ns | 1.77x | 1.67x | 1.63x | 2.03x | 2.14x |
| `attr_property` | 141.1 ns | 1.15x | 1.48x | 1.57x | 1.97x | 2.09x |
| `attr_slots` | 110.7 ns | 1.66x | 1.56x | 1.51x | 1.90x | 2.00x |
| `call_builtin` | 83.3 ns | 1.28x | 1.25x | 1.15x | 1.50x | 1.62x |
| `call_kwargs` | 204.7 ns | 1.17x | 1.20x | 1.20x | 1.51x | 1.58x |
| `call_method` | 134.0 ns | 1.30x | 1.32x | 1.39x | 1.66x | 1.80x |
| `call_simple` | 127.0 ns | 1.26x | 1.35x | 1.41x | 1.66x | 1.84x |
| `call_star_args` | 133.7 ns | 1.18x | 1.25x | 1.27x | 1.44x | 1.49x |
| `dataclass_create` | 313.6 ns | 1.32x | 1.11x | 1.55x | 1.56x | 1.65x |
| `dict_build` | 234.0 ns | 1.10x | 1.01x | 0.98x | 1.05x | 1.14x |
| `dict_get_set` | 130.3 ns | 1.34x | 1.26x | 1.18x | 1.25x | 1.29x |
| `exception_raise` | 297.1 ns | 1.14x | 1.16x | 1.09x | 1.29x | 1.35x |
| `float_arith` | 94.9 ns | 1.16x | 1.20x | 1.14x | 1.13x | 1.29x |
| `generator_yield` | 91.7 ns | 1.13x | 1.37x | 1.38x | 1.55x | 1.65x |
| `global_lookup` | 71.9 ns | 1.23x | 1.20x | 1.13x | 1.52x | 1.65x |
| `instance_create` | 307.4 ns | 1.26x | 1.31x | 1.95x | 1.91x | 1.93x |
| `int_arith` | 116.1 ns | 1.02x | 0.97x | 0.92x | 1.26x | 1.38x |
| `int_bigint` | 315.1 ns | 1.08x | 0.95x | 0.90x | 1.03x | 1.07x |
| `isinstance_check` | 91.4 ns | 1.23x | 1.19x | 1.11x | 1.34x | 1.40x |
| `list_append` | 133.4 ns | 1.59x | 1.49x | 1.41x | 1.37x | 1.44x |
| `list_comprehension` | 1.72 us | 1.15x | 1.60x | 1.63x | 1.46x | 1.58x |
| `list_index` | 203.9 ns | 1.58x | 1.37x | 1.33x | 1.49x | 1.48x |
| `local_lookup` | 58.3 ns | 1.08x | 1.03x | 0.97x | 1.36x | 1.50x |
| `set_ops` | 241.4 ns | 1.52x | 1.57x | 1.53x | 1.64x | 1.51x |
| `sort_ints` | 13.14 us | 1.00x | 0.93x | 0.94x | 0.94x | 0.94x |
| `sort_key` | 25.02 us | 1.22x | 1.03x | 1.15x | 1.19x | 1.14x |
| `str_concat` | 146.5 ns | 1.47x | 1.42x | 1.30x | 1.33x | 1.45x |
| `str_encode_decode` | 388.4 ns | 1.06x | 1.01x | 0.99x | 1.05x | 1.08x |
| `str_format` | 541.8 ns | 0.97x | 0.96x | 0.98x | 0.93x | 1.01x |
| `str_fstring` | 564.9 ns | 1.00x | 0.96x | 0.96x | 0.90x | 0.96x |
| `str_join` | 159.3 ns | 1.04x | 1.04x | 1.05x | 1.12x | 1.10x |
| `str_methods` | 756.1 ns | 1.06x | 0.92x | 0.92x | 0.92x | 0.95x |
| `str_startswith` | 276.3 ns | 1.01x | 1.07x | 2.18x | 2.22x | 2.38x |
| `try_no_exception` | 68.3 ns | 1.19x | 1.08x | 1.01x | 1.10x | 1.05x |
| `unpack_sequence` | 146.6 ns | 1.24x | 1.36x | 1.22x | 1.38x | 1.55x |
| `while_loop` | 99.2 ns | 1.43x | 1.23x | 1.12x | 1.20x | 1.19x |

### mini

| Benchmark | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 ⚠ |
| --- | --- | --- | --- | --- | --- | --- |
| `asyncio_gather` | 463.02 us | 1.35x | 1.53x | 1.53x | 1.70x | 1.74x |
| `asyncio_sleep0` | 82.54 us | 1.26x | 1.39x | 1.55x | 1.46x | 1.51x |
| `binary_trees` | 129.72 us | 1.52x | 1.69x | 1.87x | 1.85x | 1.91x |
| `deepcopy_tree` | 108.70 us | 1.38x | 1.37x | 1.40x | 2.31x | 2.46x |
| `event_loop_startup` | 37.20 us | 1.30x | 1.33x | 1.40x | 1.26x | 1.31x |
| `fib_recursive` | 238.75 us | 1.58x | 1.80x | 1.93x | 1.96x | 2.02x |
| `json_dumps` | 26.18 us | 0.99x | 1.47x | 1.42x | 1.32x | 1.79x |
| `json_loads` | 16.40 us | 0.99x | 0.94x | 0.92x | 0.89x | 0.95x |
| `matrix_multiply` | 657.22 us | 1.24x | 1.32x | 1.38x | 1.12x | 1.16x |
| `nbody` | 10.98 us | 1.38x | 1.42x | 1.38x | 1.18x | 1.21x |
| `pickle_roundtrip` | 13.24 us | 1.00x | 0.94x | 0.88x | 0.90x | 0.87x |
| `regex_compile` | 99.60 us | 1.40x | 1.38x | 1.53x | 1.46x | 1.53x |
| `regex_search` | 76.05 us | 1.08x | 0.98x | 1.03x | 0.95x | 0.95x |
| `spectral_norm` | 197.66 us | 1.44x | 1.57x | 1.56x | 1.53x | 1.87x |

### threaded

| Benchmark | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 ⚠ |
| --- | --- | --- | --- | --- | --- | --- |
| `threads_parallel` | 9.37 ms | 1.07x | 0.98x | 0.90x | 1.23x | 1.36x |
| `threads_serial` | 9.67 ms | 1.07x | 1.03x | 0.95x | 1.31x | 1.45x |
| `threads_spawn_join` | 46.19 us | 0.94x | 0.97x | 1.04x | 0.98x | 0.99x |

## Other implementations

These are separate Python implementations, not CPython builds, so they are reported apart from the version ladder. A dash means the benchmark could not run there at all.

- `rustpython` — rustpython 3.14.0.alpha, targeting Python 3.14

| Benchmark | 3.10 | rustpython | rustpython vs 3.10 |
| --- | --- | --- | --- |
| `startup_bare` | 13.34 ms | 49.79 ms | 0.268x |
| `startup_imports` | 38.95 ms | 150.50 ms | 0.259x |
| `attr_access` | 121.2 ns | 421.5 ns | 0.287x |
| `attr_property` | 141.1 ns | 470.1 ns | 0.3x |
| `attr_slots` | 110.7 ns | 359.2 ns | 0.308x |
| `call_builtin` | 83.3 ns | 299.7 ns | 0.278x |
| `call_kwargs` | 204.7 ns | 1.08 us | 0.19x |
| `call_method` | 134.0 ns | 486.1 ns | 0.276x |
| `call_simple` | 127.0 ns | 470.1 ns | 0.27x |
| `call_star_args` | 133.7 ns | 584.5 ns | 0.229x |
| `dataclass_create` | 313.6 ns | 1.21 us | 0.26x |
| `dict_build` | 234.0 ns | 1.17 us | 0.2x |
| `dict_get_set` | 130.3 ns | 538.2 ns | 0.242x |
| `exception_raise` | 297.1 ns | 1.23 us | 0.241x |
| `float_arith` | 94.9 ns | 426.3 ns | 0.223x |
| `generator_yield` | 91.7 ns | 454.6 ns | 0.202x |
| `global_lookup` | 71.9 ns | 246.9 ns | 0.291x |
| `instance_create` | 307.4 ns | 1.19 us | 0.257x |
| `int_arith` | 116.1 ns | 422.3 ns | 0.275x |
| `int_bigint` | 315.1 ns | 798.5 ns | 0.395x |
| `isinstance_check` | 91.4 ns | 366.9 ns | 0.249x |
| `list_append` | 133.4 ns | 588.6 ns | 0.227x |
| `list_comprehension` | 1.72 us | 6.73 us | 0.256x |
| `list_index` | 203.9 ns | 670.1 ns | 0.304x |
| `local_lookup` | 58.3 ns | 224.5 ns | 0.26x |
| `set_ops` | 241.4 ns | 10.37 us | 0.0233x |
| `sort_ints` | 13.14 us | 40.38 us | 0.325x |
| `sort_key` | 25.02 us | 107.80 us | 0.232x |
| `str_concat` | 146.5 ns | 444.4 ns | 0.33x |
| `str_encode_decode` | 388.4 ns | 3.04 us | 0.128x |
| `str_format` | 541.8 ns | 3.51 us | 0.154x |
| `str_fstring` | 564.9 ns | 1.98 us | 0.285x |
| `str_join` | 159.3 ns | 2.04 us | 0.0783x |
| `str_methods` | 756.1 ns | 2.86 us | 0.265x |
| `str_startswith` | 276.3 ns | 744.1 ns | 0.371x |
| `try_no_exception` | 68.3 ns | 233.9 ns | 0.292x |
| `unpack_sequence` | 146.6 ns | 663.3 ns | 0.221x |
| `while_loop` | 99.2 ns | 339.1 ns | 0.293x |
| `asyncio_gather` | 463.02 us | 4.27 ms | 0.109x |
| `asyncio_sleep0` | 82.54 us | 544.26 us | 0.152x |
| `binary_trees` | 129.72 us | 468.25 us | 0.277x |
| `deepcopy_tree` | 108.70 us | 303.48 us | 0.358x |
| `event_loop_startup` | 37.20 us | 210.28 us | 0.177x |
| `fib_recursive` | 238.75 us | 798.17 us | 0.299x |
| `json_dumps` | 26.18 us | 830.97 us | 0.0315x |
| `json_loads` | 16.40 us | 41.85 us | 0.392x |
| `matrix_multiply` | 657.22 us | 4.83 ms | 0.136x |
| `nbody` | 10.98 us | 58.10 us | 0.189x |
| `pickle_roundtrip` | 13.24 us | 3.69 ms | 0.00359x |
| `regex_compile` | 99.60 us | 4.95 us | 20.1x |
| `regex_search` | 76.05 us | 266.77 us | 0.285x |
| `spectral_norm` | 197.66 us | 735.99 us | 0.269x |
| `threads_parallel` | 9.37 ms | 21.25 ms | 0.441x |
| `threads_serial` | 9.67 ms | 34.28 ms | 0.282x |
| `threads_spawn_join` | 46.19 us | 212.21 us | 0.218x |
| **geometric mean** |  |  | **0.227x** |

## Free-threading cost

Each free-threaded build against its own GIL twin. Below `1.00x` means the free-threaded build is slower at that benchmark.

| Benchmark | 3.13t / 3.13 | 3.14t / 3.14 | 3.15t / 3.15 |
| --- | --- | --- | --- |
| `startup_bare` | 0.75x | 0.75x | 0.74x |
| `startup_imports` | 0.68x | 0.78x | 0.76x |
| `attr_access` | 0.52x | 0.75x | 0.68x |
| `attr_property` | 0.57x | 1.00x | 0.93x |
| `attr_slots` | 0.51x | 0.75x | 0.68x |
| `call_builtin` | 0.83x | 1.02x | 0.94x |
| `call_kwargs` | 0.88x | 0.93x | 0.88x |
| `call_method` | 0.85x | 1.00x | 0.93x |
| `call_simple` | 0.84x | 1.03x | 0.93x |
| `call_star_args` | 0.85x | 1.03x | 0.95x |
| `dataclass_create` | 0.58x | 0.72x | 0.70x |
| `dict_build` | 0.86x | 1.01x | 0.91x |
| `dict_get_set` | 0.72x | 0.85x | 0.80x |
| `exception_raise` | 0.97x | 0.84x | 0.81x |
| `float_arith` | 0.81x | 0.99x | 0.92x |
| `generator_yield` | 0.73x | 0.98x | 0.89x |
| `global_lookup` | 0.82x | 1.02x | 0.91x |
| `instance_create` | 0.45x | 0.79x | 0.77x |
| `int_arith` | 0.95x | 0.98x | 0.87x |
| `int_bigint` | 1.12x | 1.05x | 0.99x |
| `isinstance_check` | 0.82x | 1.02x | 0.94x |
| `list_append` | 0.63x | 0.83x | 0.85x |
| `list_comprehension` | 0.72x | 0.95x | 0.84x |
| `list_index` | 0.81x | 0.93x | 0.81x |
| `local_lookup` | 0.93x | 1.02x | 0.90x |
| `set_ops` | 0.64x | 0.74x | 0.79x |
| `sort_ints` | 1.00x | 1.01x | 0.99x |
| `sort_key` | 0.85x | 0.90x | 0.96x |
| `str_concat` | 0.70x | 1.08x | 1.02x |
| `str_encode_decode` | 0.96x | 1.07x | 1.02x |
| `str_format` | 0.96x | 1.02x | 0.93x |
| `str_fstring` | 1.06x | 1.10x | 1.01x |
| `str_join` | 0.85x | 0.89x | 0.90x |
| `str_methods` | 1.03x | 1.09x | 1.06x |
| `str_startswith` | 0.71x | 1.05x | 0.99x |
| `try_no_exception` | 0.95x | 1.11x | 0.93x |
| `unpack_sequence` | 0.61x | 1.06x | 0.94x |
| `while_loop` | 0.84x | 1.08x | 0.95x |
| `asyncio_gather` | 0.54x | 0.83x | 0.77x |
| `asyncio_sleep0` | 0.62x | 0.96x | 0.93x |
| `binary_trees` | 0.58x | 1.00x | 1.01x |
| `deepcopy_tree` | 0.64x | 0.85x | 0.92x |
| `event_loop_startup` | 0.64x | 1.02x | 0.85x |
| `fib_recursive` | 0.62x | 0.96x | 0.97x |
| `json_dumps` | 0.88x | 0.99x | 0.88x |
| `json_loads` | 0.84x | 0.87x | 0.84x |
| `matrix_multiply` | 0.50x | 0.95x | 0.85x |
| `nbody` | 0.52x | 0.84x | 0.82x |
| `pickle_roundtrip` | 0.86x | 0.87x | 0.88x |
| `regex_compile` | 0.58x | 0.89x | 0.86x |
| `regex_search` | 1.05x | 1.07x | 1.08x |
| `spectral_norm` | 0.71x | 0.96x | 0.94x |
| `threads_parallel` | 1.87x | 3.02x | 2.50x |
| `threads_serial` | 0.95x | 0.99x | 0.87x |
| `threads_spawn_join` | 0.14x | 0.12x | 0.09x |
| **geometric mean** | **0.75x** | **0.94x** | **0.89x** |

## Thread scaling

Identical CPU work run serially and across four threads. The ratio is the achieved parallel speedup; GIL builds are expected near `1.00x`.

| Interpreter | Parallel speedup |
| --- | --- |
| 3.10 | 1.03x |
| 3.11 | 1.04x |
| 3.12 | 0.98x |
| 3.13 | 0.98x |
| 3.14 | 0.97x |
| 3.15 ⚠ | 0.97x |
| 3.13t | 1.93x |
| 3.14t | 2.97x |
| 3.15t ⚠ | 2.79x |
| rustpython | 1.61x |

## Caveats

- ⚠ 3.15, 3.15t are pre-release builds; the numbers are provisional and may change before final release.
- Free-threaded builds differ from their GIL twins in build configuration as well as in the GIL, so the comparison measures both.
- Results describe the machine that produced them and do not transfer to other hardware.

