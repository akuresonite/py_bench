"""Portable host description and environment health probing.

Every probe here is best-effort: anything unavailable on the current platform
returns ``None`` rather than raising, so a sweep on Windows or macOS records the
same schema as one on a Raspberry Pi, just with fewer populated fields.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any

OK = "ok"
WARN = "warn"
NA = "na"


@dataclass
class Check:
    name: str
    status: str
    detail: str

    @property
    def is_warning(self) -> bool:
        return self.status == WARN


@dataclass
class Sample:
    """A point-in-time reading of the things that distort benchmark results."""

    temperature_c: float | None = None
    cpu_mhz: float | None = None
    throttled: str | None = None
    load_1m: float | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data = {
            "temperature_c": self.temperature_c,
            "cpu_mhz": self.cpu_mhz,
            "throttled": self.throttled,
            "load_1m": self.load_1m,
        }
        data.update(self.extras)
        return {key: value for key, value in data.items() if value is not None}


def _read_text(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read().strip("\x00 \n\t")
    except OSError:
        return None


def _run(command: list[str], timeout: float = 5.0) -> str | None:
    if not shutil.which(command[0]):
        return None
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def total_memory_bytes() -> int | None:
    if hasattr(os, "sysconf"):
        try:
            return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        except (ValueError, OSError):
            pass
    if sys.platform == "darwin":
        value = _run(["sysctl", "-n", "hw.memsize"])
        if value and value.isdigit():
            return int(value)
    if sys.platform == "win32":
        try:
            import ctypes

            class _MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = _MemoryStatus()
            status.dwLength = ctypes.sizeof(_MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
        except Exception:
            return None
    return None


def cpu_model() -> str | None:
    """A human-readable name for the machine or its CPU."""
    board = _read_text("/sys/firmware/devicetree/base/model")
    if board:
        return board
    if sys.platform.startswith("linux"):
        cpuinfo = _read_text("/proc/cpuinfo") or ""
        for line in cpuinfo.splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    if sys.platform == "darwin":
        return _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    return platform.processor() or None


def governor() -> str | None:
    return _read_text("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")


def cpu_mhz() -> float | None:
    raw = _read_text("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    if raw and raw.isdigit():
        return int(raw) / 1000.0
    return None


def temperature_c() -> float | None:
    for zone in range(4):
        raw = _read_text("/sys/class/thermal/thermal_zone%d/temp" % zone)
        if raw and raw.lstrip("-").isdigit():
            value = int(raw)
            return value / 1000.0 if abs(value) > 1000 else float(value)
    measured = _run(["vcgencmd", "measure_temp"])
    if measured and "=" in measured:
        try:
            return float(measured.split("=", 1)[1].rstrip("'C"))
        except ValueError:
            return None
    return None


#: Raspberry Pi ``get_throttled`` bit meanings. Bits 0-3 describe the *current*
#: state; bits 16-19 are sticky "has happened since boot" flags that never clear,
#: so only the current bits may invalidate a measurement.
THROTTLE_BITS = {
    0: "under-voltage detected",
    1: "arm frequency capped",
    2: "currently throttled",
    3: "soft temperature limit active",
    16: "under-voltage has occurred",
    17: "arm frequency capping has occurred",
    18: "throttling has occurred",
    19: "soft temperature limit has occurred",
}
CURRENT_THROTTLE_MASK = 0xF
STICKY_THROTTLE_MASK = 0xF0000


def throttled() -> str | None:
    """Raspberry Pi throttle bits, e.g. ``0x0`` when healthy."""
    value = _run(["vcgencmd", "get_throttled"])
    if value and "=" in value:
        return value.split("=", 1)[1]
    return None


def decode_throttled(value: str | None) -> tuple[list[str], list[str]]:
    """Split throttle bits into (current problems, sticky since-boot problems)."""
    if not value:
        return [], []
    try:
        bits = int(value, 16 if value.lower().startswith("0x") else 10)
    except ValueError:
        return [], []
    current = [text for bit, text in THROTTLE_BITS.items()
               if bit < 16 and bits & (1 << bit)]
    sticky = [text for bit, text in THROTTLE_BITS.items()
              if bit >= 16 and bits & (1 << bit)]
    return current, sticky


def on_battery() -> bool | None:
    """True when running on battery, which invalidates timing comparisons."""
    if sys.platform.startswith("linux"):
        supply_root = "/sys/class/power_supply"
        try:
            entries = os.listdir(supply_root)
        except OSError:
            return None
        found_mains = False
        for entry in entries:
            kind = _read_text(os.path.join(supply_root, entry, "type"))
            if kind == "Mains":
                found_mains = True
                online = _read_text(os.path.join(supply_root, entry, "online"))
                if online == "1":
                    return False
        return True if found_mains else None
    if sys.platform == "darwin":
        output = _run(["pmset", "-g", "batt"])
        if output:
            return "Battery Power" in output
        return None
    if sys.platform == "win32":
        try:
            import ctypes

            class _PowerStatus(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_byte),
                    ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte),
                    ("SystemStatusFlag", ctypes.c_byte),
                    ("BatteryLifeTime", ctypes.c_ulong),
                    ("BatteryFullLifeTime", ctypes.c_ulong),
                ]

            status = _PowerStatus()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                if status.ACLineStatus == 128:  # no battery present
                    return False
                return status.ACLineStatus == 0
        except Exception:
            return None
    return None


def load_1m() -> float | None:
    getloadavg = getattr(os, "getloadavg", None)
    if getloadavg is None:
        return None
    try:
        return getloadavg()[0]
    except OSError:
        return None


def pin_command(cpus: str | None) -> list[str]:
    """Prefix that pins a subprocess to specific cores, or [] if unsupported."""
    if not cpus:
        return []
    if sys.platform.startswith("linux") and shutil.which("taskset"):
        return ["taskset", "-c", cpus]
    return []


def pinning_available() -> bool:
    return sys.platform.startswith("linux") and shutil.which("taskset") is not None


def host_info() -> dict[str, Any]:
    memory = total_memory_bytes()
    return {
        "model": cpu_model(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "cpu_count": os.cpu_count(),
        "memory_bytes": memory,
        "memory_gib": round(memory / (1024 ** 3), 2) if memory else None,
        "governor": governor(),
        "host_python": ".".join(str(part) for part in sys.version_info[:3]),
    }


def sample() -> Sample:
    return Sample(
        temperature_c=temperature_c(),
        cpu_mhz=cpu_mhz(),
        throttled=throttled(),
        load_1m=load_1m(),
    )


def is_degraded(before: Sample, after: Sample, governor_name: str | None) -> str | None:
    """Return a reason string when a measurement should not be trusted."""
    for reading in (before, after):
        current, _sticky = decode_throttled(reading.throttled)
        if current:
            return "soc throttling during run: %s" % ", ".join(current)
        if reading.temperature_c is not None and reading.temperature_c >= 80.0:
            return "cpu temperature %.1f C" % reading.temperature_c
    if governor_name is not None and governor_name not in ("performance",):
        return "cpu governor is %r, not 'performance'" % governor_name
    load = after.load_1m if after.load_1m is not None else before.load_1m
    cpus = os.cpu_count() or 1
    if load is not None and load > cpus * 1.5:
        return "system load %.2f on %d cpus" % (load, cpus)
    return None


def checks() -> list[Check]:
    """Human-facing readiness report used by ``pybench doctor``."""
    results: list[Check] = []

    governor_name = governor()
    if governor_name is None:
        results.append(Check("cpu governor", NA, "not exposed on this platform"))
    elif governor_name == "performance":
        results.append(Check("cpu governor", OK, governor_name))
    else:
        results.append(Check(
            "cpu governor", WARN,
            "%s — frequency scaling adds noise; set 'performance' for stable runs"
            % governor_name,
        ))

    throttle = throttled()
    current, sticky = decode_throttled(throttle)
    if throttle is None:
        results.append(Check("soc throttling", NA, "no vcgencmd on this platform"))
    elif current:
        results.append(Check("soc throttling", WARN,
                             "happening now: %s" % ", ".join(current)))
    elif sticky:
        results.append(Check("soc throttling", WARN,
                             "clear now, but since boot: %s (check power supply "
                             "and cooling)" % ", ".join(sticky)))
    else:
        results.append(Check("soc throttling", OK, "no throttling recorded"))

    temperature = temperature_c()
    if temperature is None:
        results.append(Check("temperature", NA, "no thermal sensor found"))
    elif temperature < 70:
        results.append(Check("temperature", OK, "%.1f C" % temperature))
    else:
        results.append(Check("temperature", WARN, "%.1f C — let the machine cool" % temperature))

    battery = on_battery()
    if battery is None:
        results.append(Check("power source", NA, "unknown"))
    elif battery:
        results.append(Check("power source", WARN, "on battery — plug in before benchmarking"))
    else:
        results.append(Check("power source", OK, "mains"))

    load = load_1m()
    cpus = os.cpu_count() or 1
    if load is None:
        results.append(Check("system load", NA, "load average unavailable"))
    elif load <= cpus * 0.5:
        results.append(Check("system load", OK, "%.2f on %d cpus" % (load, cpus)))
    else:
        results.append(Check("system load", WARN,
                             "%.2f on %d cpus — close other work" % (load, cpus)))

    if pinning_available():
        results.append(Check("cpu pinning", OK, "taskset available (--pin)"))
    else:
        results.append(Check("cpu pinning", NA, "taskset unavailable; --pin is ignored"))

    free_gib = shutil.disk_usage(os.getcwd()).free / (1024 ** 3)
    if free_gib >= 5:
        results.append(Check("free disk", OK, "%.1f GiB" % free_gib))
    else:
        results.append(Check("free disk", WARN,
                             "%.1f GiB — interpreter downloads need ~2 GiB" % free_gib))

    return results
