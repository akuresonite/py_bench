"""The interpreter matrix: what to test, how to obtain it, what it is.

Interpreters come from ``uv``'s python-build-standalone distributions so that
every build in the matrix shares a toolchain and optimisation configuration —
a difference in the numbers is then a difference in CPython, not in packaging.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any

#: Minor versions under test, oldest first.
MINORS = ["3.10", "3.11", "3.12", "3.13", "3.14", "3.15"]

#: Minor versions that also ship a free-threaded (no-GIL) build.
FREETHREADED_MINORS = ["3.13", "3.14", "3.15"]

#: Minor versions that are not yet final releases; their numbers are provisional.
PRERELEASE_MINORS = ["3.15"]

#: The timing driver ships inside the package so it is found however pybench was
#: installed — from a clone, an editable install, or a built wheel.
DRIVER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "benchmarks", "_driver.py"
)


@dataclass
class Interpreter:
    key: str                    # "3.13" or "3.13t"
    minor: str                  # "3.13"
    request: str                # what uv was asked for
    freethreaded: bool = False
    path: str | None = None
    source: str = "uv"          # "uv" | "system" | "path"
    implementation: str = "cpython"
    #: Reference interpreters define the benchmark catalogue. An alternative
    #: implementation that cannot run a benchmark records a failure for that cell
    #: instead of removing the benchmark from everyone else's comparison.
    reference: bool = True
    available: bool = False
    reason: str | None = None
    probe: dict[str, Any] = field(default_factory=dict)

    @property
    def prerelease(self) -> bool:
        return self.minor in PRERELEASE_MINORS

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "minor": self.minor,
            "request": self.request,
            "freethreaded": self.freethreaded,
            "prerelease": self.prerelease,
            "implementation": self.implementation,
            "reference": self.reference,
            "path": self.path,
            "source": self.source,
            "available": self.available,
            "reason": self.reason,
            "probe": self.probe,
        }


def matrix(
    minors: list[str] | None = None,
    include_freethreaded: bool = True,
) -> list[Interpreter]:
    """Build the full interpreter matrix, standard builds first."""
    selected = list(minors or MINORS)
    entries: list[Interpreter] = []
    for minor in selected:
        entries.append(Interpreter(key=minor, minor=minor, request=minor))
    if include_freethreaded:
        for minor in selected:
            if minor in FREETHREADED_MINORS:
                entries.append(
                    Interpreter(
                        key=minor + "t",
                        minor=minor,
                        request=minor + "t",
                        freethreaded=True,
                    )
                )
    return entries


def extra_interpreter(key: str, path: str) -> Interpreter:
    """An interpreter supplied by path rather than resolved through uv.

    Used for alternative implementations (RustPython, PyPy, GraalPy) and for
    locally built CPythons. These are never reference interpreters.
    """
    return Interpreter(
        key=key,
        minor="",
        request=path,
        path=path,
        source="path",
        implementation="unknown",
        reference=False,
    )


def parse_extra(spec: str) -> Interpreter:
    """Parse a ``KEY=PATH`` (or bare ``PATH``) command line value."""
    key, separator, path = spec.partition("=")
    if not separator:
        path = key
        key = os.path.splitext(os.path.basename(path))[0]
    key, path = key.strip(), path.strip()
    if not path:
        raise ValueError("expected KEY=PATH, got %r" % spec)
    resolved = shutil.which(path) or path
    return extra_interpreter(key, resolved)


def find_rustpython(path: str | None = None) -> Interpreter | None:
    """Locate a RustPython binary, on PATH or where cargo installs it."""
    candidates = [path] if path else []
    candidates.append(shutil.which("rustpython"))
    candidates.append(os.path.expanduser("~/.cargo/bin/rustpython"))
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return extra_interpreter("rustpython", candidate)
    return None


def uv_available() -> bool:
    return shutil.which("uv") is not None


def _uv(args: list[str], timeout: float = 1800.0) -> subprocess.CompletedProcess:
    """Run uv, converting a timeout or launch failure into a failed result."""
    try:
        return subprocess.run(
            ["uv"] + args, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args, returncode=124, stdout="",
            stderr="error: uv timed out after %.0fs (another uv process may hold "
                   "the lock)" % timeout,
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            args, returncode=127, stdout="", stderr="error: could not run uv: %s" % exc
        )


def install(entries: list[Interpreter], reinstall: bool = False) -> list[Interpreter]:
    """Ask uv for every interpreter in the matrix. Missing builds are recorded."""
    if not uv_available():
        for entry in entries:
            entry.available = False
            entry.reason = "uv is not installed (see https://docs.astral.sh/uv/)"
        return entries

    for entry in entries:
        args = ["python", "install", entry.request]
        if reinstall:
            args.append("--reinstall")
        completed = _uv(args)
        if completed.returncode != 0:
            entry.available = False
            entry.reason = _first_error(completed.stderr) or "uv install failed"
    return resolve(entries)


def _first_error(stderr: str) -> str | None:
    for line in (stderr or "").splitlines():
        line = line.strip()
        if line.lower().startswith("error"):
            return line[:200]
    return None


def resolve(
    entries: list[Interpreter], allow_system: bool = False
) -> list[Interpreter]:
    """Locate each interpreter on disk and probe it. Never raises."""
    catalogue_of_installed = installed_pythons() if uv_available() else []
    for entry in entries:
        if entry.source == "path":
            _resolve_by_path(entry)
            continue
        path = _match_installed(entry, catalogue_of_installed)
        if path is None and uv_available():
            path = _find_uv(entry.request)
        if path is None and allow_system:
            path = _find_system(entry)
            if path is not None:
                entry.source = "system"
        if path is None:
            entry.available = False
            entry.path = None
            if entry.reason is None:
                entry.reason = "not installed for this platform"
            continue
        entry.path = path
        probe = probe_interpreter(path)
        if probe is None:
            entry.available = False
            entry.reason = "interpreter found but failed to run the driver"
            continue
        if entry.freethreaded and not probe.get("freethreaded_build"):
            entry.available = False
            entry.reason = "resolved build is not free-threaded"
            continue
        entry.probe = probe
        entry.available = True
        entry.reason = None
    return entries


@dataclass
class _Installed:
    version: str
    minor: str
    freethreaded: bool
    path: str
    managed: bool


def uv_python_dir() -> str | None:
    completed = _uv(["python", "dir"], timeout=60.0)
    if completed.returncode != 0:
        return None
    path = completed.stdout.strip()
    return path or None


def installed_pythons() -> list[_Installed]:
    """Parse ``uv python list --only-installed`` once, instead of probing per entry."""
    completed = _uv(["python", "list", "--only-installed"], timeout=120.0)
    if completed.returncode != 0:
        return []
    managed_root = uv_python_dir()
    found: list[_Installed] = []
    for line in completed.stdout.splitlines():
        # Rows are "<key><padding><path>", optionally "<path> -> <target>". Split
        # once so that paths containing spaces (common on Windows) survive intact.
        head = line.split(None, 1)
        if len(head) < 2:
            continue
        key, path = head[0], head[1].strip()
        if " -> " in path:
            # A symlink row; the interpreter it points at is listed separately.
            continue
        if not key.startswith("cpython-"):
            continue
        descriptor = key.split("-", 2)[1] if key.count("-") >= 2 else ""
        version, _, variant = descriptor.partition("+")
        match = re.match(r"^(\d+\.\d+)", version)
        if not match or not os.path.exists(path):
            continue
        found.append(_Installed(
            version=version,
            minor=match.group(1),
            freethreaded=("freethreaded" in variant),
            path=path,
            managed=bool(managed_root and path.startswith(managed_root)),
        ))
    return found


def _resolve_by_path(entry: Interpreter) -> None:
    """Probe an interpreter given directly by path, whatever implementation it is."""
    if not entry.path or not os.path.exists(entry.path):
        entry.available = False
        entry.reason = "no such interpreter: %s" % (entry.path or "")
        return
    probe = probe_interpreter(entry.path)
    if probe is None:
        entry.available = False
        entry.reason = "interpreter found but failed to run the driver"
        return
    entry.probe = probe
    entry.implementation = probe.get("implementation", "unknown")
    entry.freethreaded = bool(probe.get("freethreaded_build"))
    entry.minor = ".".join(probe.get("version", "").split(".")[:2])
    entry.available = True
    entry.reason = None


def _find_uv(request: str) -> str | None:
    completed = _uv(["python", "find", request], timeout=180.0)
    if completed.returncode != 0:
        return None
    path = completed.stdout.strip()
    return path if path and os.path.exists(path) else None


def _match_installed(
    entry: Interpreter, catalogue: list[_Installed]
) -> str | None:
    """Pick the best installed build for a matrix entry, preferring uv-managed ones."""
    candidates = [
        item for item in catalogue
        if item.minor == entry.minor and item.freethreaded == entry.freethreaded
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda item: (not item.managed, item.version), reverse=False)
    managed = [item for item in candidates if item.managed]
    return (managed or candidates)[0].path


def _find_system(entry: Interpreter) -> str | None:
    """Fall back to an interpreter already on PATH (marks the sweep mixed-source)."""
    if entry.freethreaded:
        candidates = ["python%st" % entry.minor, "python%s-freethreading" % entry.minor]
    else:
        candidates = ["python%s" % entry.minor]
        if sys.platform == "win32":
            candidates.append("python")
    for name in candidates:
        found = shutil.which(name)
        if found:
            probe = probe_interpreter(found)
            if probe and probe.get("version", "").startswith(entry.minor + "."):
                if entry.freethreaded == bool(probe.get("freethreaded_build")):
                    return found
    return None


def probe_interpreter(path: str) -> dict[str, Any] | None:
    """Run the driver's probe command inside the target interpreter."""
    try:
        completed = subprocess.run(
            [path, DRIVER, "probe"],
            capture_output=True, text=True, timeout=120.0, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None


def catalogue(path: str) -> list[dict[str, Any]] | None:
    """Ask a target interpreter which benchmarks it can import."""
    try:
        completed = subprocess.run(
            [path, DRIVER, "list"],
            capture_output=True, text=True, timeout=120.0, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout)["benchmarks"]
    except (json.JSONDecodeError, KeyError):
        return None


def describe(entry: Interpreter) -> str:
    """One-line human description of a resolved interpreter."""
    if not entry.available:
        return "%-6s unavailable — %s" % (entry.key, entry.reason or "unknown")
    probe = entry.probe
    bits = []
    if entry.implementation not in ("cpython", ""):
        bits.append(entry.implementation)
    bits.append(probe.get("version_display") or probe.get("version", "?"))
    if entry.freethreaded:
        gil = probe.get("gil_enabled")
        bits.append("free-threaded, GIL %s" % ("on" if gil else "off"))
    jit = probe.get("jit") or {}
    if jit.get("built"):
        bits.append("JIT %s" % ("enabled" if jit.get("enabled") else "built, off"))
    else:
        bits.append("no JIT")
    if entry.prerelease:
        bits.append("PRERELEASE")
    return "%-6s %s" % (entry.key, "  ".join(bits))
