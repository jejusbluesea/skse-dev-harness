"""Shared paths and helpers for the Skyrim SKSE test harness tools."""

from __future__ import annotations

import ctypes
import re
import subprocess
import sys
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY_ROOT = Path(r"D:\SkyrimLibrary")

SKSE_SCRIPTS_MOD = "Skyrim Script Extender (SKSE64)"
ADDRESS_LIBRARY_MOD = "Address Library for SKSE Plugins"
DEV_PREFIX = "[DEV] "

BASE_PROFILE = "01 - SKSE Base"
LEGACY_BASE_PROFILE = "01 - SKSE"
DEV_PROFILE = "02 - Dev Sanity"

PASS, WARN, FAIL, UNKNOWN = "PASS", "WARN", "FAIL", "UNKNOWN"


@dataclass(frozen=True)
class Runtime:
    name: str  # folder name, e.g. "1.6.1170"
    skse: str  # expected SKSE version, e.g. "2.2.8"

    @property
    def version(self) -> tuple[int, int, int, int]:
        major, minor, build = (int(p) for p in self.name.split("."))
        return (major, minor, build, 0)

    @property
    def game_dir(self) -> Path:
        return LIBRARY_ROOT / self.name

    @property
    def mo2_dir(self) -> Path:
        return LIBRARY_ROOT / "MO2" / self.name

    @property
    def skse_dll(self) -> str:
        return "skse64_{}_{}_{}.dll".format(*self.version[:3])

    @property
    def address_library_bin(self) -> str:
        # 1.5.x uses "version-", 1.6+ uses "versionlib-".
        prefix = "version" if self.version[:2] == (1, 5) else "versionlib"
        return "{}-{}-{}-{}-{}.bin".format(prefix, *self.version)

    def profile_dir(self, profile: str) -> Path:
        return self.mo2_dir / "profiles" / profile

    def mod_dir(self, mod: str) -> Path:
        return self.mo2_dir / "mods" / mod


RUNTIMES = {
    r.name: r
    for r in (
        Runtime("1.5.97", "2.0.20"),
        Runtime("1.6.1170", "2.2.8"),
        Runtime("1.7.104", "2.3.1"),
    )
}


def select_runtimes(name: str) -> list[Runtime]:
    if name == "all":
        return list(RUNTIMES.values())
    if name not in RUNTIMES:
        sys.exit(f"unknown runtime '{name}' (choose from: all, {', '.join(RUNTIMES)})")
    return [RUNTIMES[name]]


def file_version(path: Path) -> tuple[int, int, int, int] | None:
    """Reads the fixed file version of a PE file, or None if it has none."""
    version_dll = ctypes.WinDLL("version", use_last_error=True)
    size = version_dll.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        return None
    buffer = ctypes.create_string_buffer(size)
    if not version_dll.GetFileVersionInfoW(str(path), 0, size, buffer):
        return None
    info = ctypes.c_void_p()
    length = wintypes.UINT()

    # Prefer the FileVersion string: SkyrimSE.exe 1.5.97 carries 1.0.0.0 in its fixed version block.
    if version_dll.VerQueryValueW(buffer, "\\VarFileInfo\\Translation", ctypes.byref(info), ctypes.byref(length)) and length.value >= 4:
        language, codepage = ctypes.cast(info, ctypes.POINTER(wintypes.WORD * 2)).contents
        key = f"\\StringFileInfo\\{language:04x}{codepage:04x}\\FileVersion"
        if version_dll.VerQueryValueW(buffer, key, ctypes.byref(info), ctypes.byref(length)) and length.value:
            parts = re.findall(r"\d+", ctypes.wstring_at(info.value))
            if len(parts) == 4:
                return tuple(int(p) for p in parts)

    if not version_dll.VerQueryValueW(buffer, "\\", ctypes.byref(info), ctypes.byref(length)):
        return None
    # VS_FIXEDFILEINFO: signature, struct version, file version MS, file version LS, ...
    fields = ctypes.cast(info, ctypes.POINTER(wintypes.DWORD * 4)).contents
    ms, ls = fields[2], fields[3]
    return (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)


def format_version(version: tuple[int, ...] | None) -> str:
    return ".".join(str(p) for p in version) if version else "?"


def running_executables() -> list[Path] | None:
    """Paths of running ModOrganizer/Skyrim processes, or None if that cannot be determined."""
    command = (
        "Get-Process ModOrganizer,SkyrimSE,skse64_loader -ErrorAction SilentlyContinue"
        " | ForEach-Object { $_.Path }"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def is_instance_busy(runtime: Runtime) -> bool | None:
    """True if MO2 or the game of this runtime is running; None if unknown."""
    running = running_executables()
    if running is None:
        return None
    roots = (runtime.mo2_dir, runtime.game_dir)
    return any(root in exe.parents for exe in running for root in roots)


def read_modlist(profile_dir: Path) -> dict[str, bool] | None:
    """Managed mods of a profile mapped to their enabled state, in priority order (highest first)."""
    modlist = profile_dir / "modlist.txt"
    if not modlist.is_file():
        return None
    mods: dict[str, bool] = {}
    for line in modlist.read_text(encoding="utf-8").splitlines():
        if line[:1] in "+-" and line[1:]:
            mods[line[1:]] = line[0] == "+"
    return mods
