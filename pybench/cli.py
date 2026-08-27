"""Command line interface for pybench."""

from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import Any

from . import __version__, environment, interpreters
from .report import markdown as markdown_report
from .report import table as table_report
from .results import Sweep
from .runner import RunConfig, run_sweep

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
REPORTS_DIR = os.path.join(ROOT, "reports")


def _matrix_from_args(args: argparse.Namespace) -> list[interpreters.Interpreter]:
    minors = [item.strip() for item in args.minors.split(",")] if args.minors else None
    return interpreters.matrix(
        minors=minors, include_freethreaded=not args.no_freethreaded
    )


def _require_uv() -> bool:
    if interpreters.uv_available():
        return True
    sys.stderr.write(
        "uv is not installed, and pybench uses it to fetch matching CPython builds.\n"
        "Install it from https://docs.astral.sh/uv/getting-started/installation/\n"
        "or re-run with --allow-system to benchmark interpreters already on PATH.\n"
    )
    return False


def command_doctor(args: argparse.Namespace) -> int:
    host = environment.host_info()
    print("host      %s (%s, %s cores, %s GiB)" % (
        host.get("model") or host.get("processor") or "unknown",
        host.get("machine"), host.get("cpu_count"), host.get("memory_gib")))
    print("system    %s %s" % (host.get("system"), host.get("release")))
    print("python    %s (harness host interpreter)" % host.get("host_python"))
    print("uv        %s" % ("found" if interpreters.uv_available() else "NOT FOUND"))
    print()
    warnings = 0
    for check in environment.checks():
        marker = {"ok": "ok  ", "warn": "WARN", "na": "n/a "}[check.status]
        print("  %s %-16s %s" % (marker, check.name, check.detail))
        warnings += 1 if check.is_warning else 0
    print()
    if warnings:
        print("%d warning(s). Benchmarks still run, but affected measurements are "
              "marked 'degraded' in the results." % warnings)
        if host.get("governor") not in (None, "performance"):
            print("To pin the CPU governor for a session (Linux):")
            print("  sudo cpupower frequency-set -g performance")
            print("  # or: for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; "
                  "do echo performance | sudo tee $f >/dev/null; done")
    else:
        print("Environment looks good.")
    return 0


def command_install(args: argparse.Namespace) -> int:
    if not interpreters.uv_available():
        _require_uv()
        return 1
    entries = _matrix_from_args(args)
    print("Installing %d interpreter(s) via uv. First run downloads ~2 GiB.\n"
          % len(entries))
    resolved = interpreters.install(entries, reinstall=args.reinstall)
    for entry in resolved:
        print("  " + interpreters.describe(entry))
    missing = [entry for entry in resolved if not entry.available]
    print("\n%d of %d available." % (len(resolved) - len(missing), len(resolved)))
    return 0


def command_list(args: argparse.Namespace) -> int:
    entries = interpreters.resolve(
        _matrix_from_args(args), allow_system=args.allow_system
    )
    for entry in entries:
        print("  " + interpreters.describe(entry))
        if entry.available and entry.path:
            print("         %s" % entry.path)
    available = [entry for entry in entries if entry.available]
    print("\n%d of %d available." % (len(available), len(entries)))
    if available:
        found = interpreters.catalogue(available[0].path)
        if found:
            groups: dict[str, int] = {}
            for item in found:
                groups[item["group"]] = groups.get(item["group"], 0) + 1
            summary = ", ".join("%d %s" % (count, name) for name, count in sorted(groups.items()))
            print("%d benchmarks (%s) plus 2 startup benchmarks."
                  % (len(found), summary))
    return 0


def command_run(args: argparse.Namespace) -> int:
    entries = interpreters.resolve(
        _matrix_from_args(args), allow_system=args.allow_system
    )
    available = [entry for entry in entries if entry.available]
    if not available:
        sys.stderr.write("No interpreters available. Run 'pybench install' first.\n")
        _require_uv()
        return 1

    config = RunConfig(
        min_time_ms=args.min_time_ms,
        warmup=args.warmup,
        rounds=args.rounds,
        repeats=args.repeats,
        pin=args.pin,
        groups=args.group or None,
        only=args.only or None,
    )

    print("Benchmarking %d interpreter(s): %s"
          % (len(available), ", ".join(entry.key for entry in available)))
    for entry in entries:
        if not entry.available:
            print("  skipping %s — %s" % (entry.key, entry.reason))
    if args.pin and not environment.pinning_available():
        print("  note: --pin requested but taskset is unavailable here; ignoring.")
    print()

    sweep = run_sweep(available, config, on_progress=lambda line: print(line, flush=True))

    output = args.output or os.path.join(
        RESULTS_DIR, "sweep-%s.json" % sweep.sweep_id
    )
    sweep.save(output)
    print("\nResults written to %s" % os.path.relpath(output, os.getcwd()))

    table_report.render(sweep, baseline=args.baseline)
    if not args.no_markdown:
        path = _write_markdown(sweep, args.baseline)
        print("Markdown report written to %s" % os.path.relpath(path, os.getcwd()))
    return 0


def command_report(args: argparse.Namespace) -> int:
    path = args.path or _latest_result()
    if path is None:
        sys.stderr.write("No results found. Run 'pybench run' first.\n")
        return 1
    sweep = Sweep.load(path)
    if args.format in ("table", "both"):
        table_report.render(sweep, baseline=args.baseline)
    if args.format in ("markdown", "both"):
        written = _write_markdown(sweep, args.baseline)
        print("Markdown report written to %s" % os.path.relpath(written, os.getcwd()))
    return 0


def _write_markdown(sweep: Sweep, baseline: str | None) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, "sweep-%s.md" % sweep.sweep_id)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(markdown_report.render(sweep, baseline=baseline))
    return path


def _latest_result() -> str | None:
    found = sorted(glob.glob(os.path.join(RESULTS_DIR, "sweep-*.json")))
    return found[-1] if found else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pybench",
        description="Compare CPython execution speed across interpreter versions.",
    )
    parser.add_argument("--version", action="version", version="pybench %s" % __version__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_matrix_options(target: argparse.ArgumentParser) -> None:
        target.add_argument(
            "--minors",
            help="comma-separated minor versions (default: %s)"
                 % ",".join(interpreters.MINORS),
        )
        target.add_argument(
            "--no-freethreaded", action="store_true",
            help="skip the free-threaded (no-GIL) builds",
        )

    doctor = sub.add_parser("doctor", help="check whether this machine is fit to benchmark")
    doctor.set_defaults(func=command_doctor)

    install = sub.add_parser("install", help="download the interpreter matrix with uv")
    add_matrix_options(install)
    install.add_argument("--reinstall", action="store_true",
                         help="force uv to reinstall each interpreter")
    install.set_defaults(func=command_install)

    listing = sub.add_parser("list", help="show the resolved matrix and benchmark catalogue")
    add_matrix_options(listing)
    listing.add_argument("--allow-system", action="store_true",
                         help="fall back to interpreters already on PATH")
    listing.set_defaults(func=command_list)

    run = sub.add_parser("run", help="execute a sweep")
    add_matrix_options(run)
    run.add_argument("--allow-system", action="store_true",
                     help="fall back to interpreters already on PATH (marks the sweep "
                          "mixed-source)")
    run.add_argument("--min-time-ms", type=float, default=50.0,
                     help="minimum duration of a single measurement (default: 50)")
    run.add_argument("--warmup", type=int, default=2,
                     help="warmup rounds discarded per measurement (default: 2)")
    run.add_argument("--rounds", type=int, default=5,
                     help="measured rounds per measurement (default: 5)")
    run.add_argument("--repeats", type=int, default=1,
                     help="times to repeat the whole matrix (default: 1)")
    run.add_argument("--pin", help="pin subprocesses to these cpus, e.g. 2,3 (Linux only)")
    run.add_argument("--group", action="append",
                     help="limit to a benchmark group (startup, micro, mini, threaded); "
                          "repeatable")
    run.add_argument("--only", action="append",
                     help="limit to benchmarks whose id contains this text; repeatable")
    run.add_argument("--baseline", help="interpreter to compare against (default: oldest)")
    run.add_argument("--output", help="where to write the results JSON")
    run.add_argument("--no-markdown", action="store_true",
                     help="skip writing the markdown report")
    run.set_defaults(func=command_run)

    report = sub.add_parser("report", help="render a report from a results file")
    report.add_argument("path", nargs="?", help="results JSON (default: most recent)")
    report.add_argument("--baseline", help="interpreter to compare against")
    report.add_argument("--format", choices=["table", "markdown", "both"],
                        default="table")
    report.set_defaults(func=command_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted.\n")
        return 130
    except RuntimeError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
