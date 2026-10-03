"""Static (filesystem) verification of a runtime's game copy and MO2 profile.

    python tools/check_env.py                       # all runtimes, "02 - Dev Sanity"
    python tools/check_env.py --runtime 1.7.104 --profile "01 - SKSE Base"

Exit code is 1 if any check FAILs. UNKNOWN is reported but is not a failure.
"""

from __future__ import annotations

import argparse
import sys

import harness
from harness import FAIL, PASS, UNKNOWN, WARN


class Report:
    def __init__(self) -> None:
        self.counts = {PASS: 0, WARN: 0, FAIL: 0, UNKNOWN: 0}

    def add(self, status: str, message: str) -> None:
        self.counts[status] += 1
        print(f"  [{status:<7}] {message}")


def check_game(runtime: harness.Runtime, report: Report) -> None:
    exe = runtime.game_dir / "SkyrimSE.exe"
    if not exe.is_file():
        report.add(FAIL, f"SkyrimSE.exe not found in {runtime.game_dir}")
        return
    version = harness.file_version(exe)
    if version is None:
        report.add(UNKNOWN, "SkyrimSE.exe file version could not be read")
    elif version == runtime.version:
        report.add(PASS, f"SkyrimSE.exe {harness.format_version(version)}")
    else:
        report.add(FAIL, f"SkyrimSE.exe is {harness.format_version(version)}, expected {harness.format_version(runtime.version)}")

    loader = runtime.game_dir / "skse64_loader.exe"
    if not loader.is_file():
        report.add(FAIL, "skse64_loader.exe not found")
    else:
        # The loader's file version is 0.<major>.<minor>.<build>.
        loader_version = harness.file_version(loader)
        if loader_version is None:
            report.add(UNKNOWN, "skse64_loader.exe file version could not be read")
        elif harness.format_version(loader_version[1:]) == runtime.skse:
            report.add(PASS, f"skse64_loader.exe {runtime.skse}")
        else:
            report.add(FAIL, f"skse64_loader.exe is {harness.format_version(loader_version[1:])}, expected {runtime.skse}")

    skse_dlls = sorted(p.name for p in runtime.game_dir.glob("skse64_[0-9]*.dll"))
    if runtime.skse_dll in skse_dlls:
        report.add(PASS, f"{runtime.skse_dll} present")
    else:
        report.add(FAIL, f"{runtime.skse_dll} not found (found: {', '.join(skse_dlls) or 'none'})")
    for stray in skse_dlls:
        if stray != runtime.skse_dll:
            report.add(WARN, f"SKSE runtime DLL for another game version in game root: {stray}")

    root_plugins = sorted(p.name for p in (runtime.game_dir / "Data" / "SKSE" / "Plugins").glob("*.dll"))
    if root_plugins:
        report.add(WARN, f"plugin DLLs installed directly in the game Data folder: {', '.join(root_plugins)}")


def check_profile(runtime: harness.Runtime, profile: str, report: Report) -> None:
    busy = harness.is_instance_busy(runtime)
    if busy is None:
        report.add(UNKNOWN, "could not determine whether MO2/Skyrim is running")
    elif busy:
        report.add(WARN, "MO2 or Skyrim of this runtime is running; profile state may still change")

    mods = harness.read_modlist(runtime.profile_dir(profile))
    if mods is None:
        report.add(UNKNOWN, f"profile '{profile}' has no modlist.txt (profile not created yet?)")
        return
    enabled = [name for name, on in mods.items() if on]

    for required in (harness.SKSE_SCRIPTS_MOD, harness.ADDRESS_LIBRARY_MOD):
        if required not in mods:
            report.add(FAIL, f"mod not installed: {required}")
        elif mods[required]:
            report.add(PASS, f"enabled: {required}")
        else:
            report.add(FAIL, f"disabled: {required}")

    address_bin = runtime.mod_dir(harness.ADDRESS_LIBRARY_MOD) / "SKSE" / "Plugins" / runtime.address_library_bin
    if not address_bin.is_file():
        report.add(FAIL, f"Address Library file missing: {runtime.address_library_bin}")
    elif mods.get(harness.ADDRESS_LIBRARY_MOD):
        report.add(PASS, f"Address Library file: {runtime.address_library_bin}")
    else:
        report.add(WARN, f"{runtime.address_library_bin} exists but its mod is disabled")

    dev_mods = [name for name in mods if name.startswith(harness.DEV_PREFIX)]
    is_dev_profile = profile == harness.DEV_PROFILE
    if not dev_mods:
        report.add(WARN if is_dev_profile else PASS, "no [DEV] mod in this profile")
    for name in dev_mods:
        if mods[name]:
            report.add(PASS if is_dev_profile else WARN, f"[DEV] mod enabled: {name}")
        else:
            report.add(WARN if is_dev_profile else PASS, f"[DEV] mod disabled: {name}")

    # Plugin DLLs the virtual Data folder will contain, highest priority first.
    for name in enabled:
        mod_dir = runtime.mod_dir(name)
        if not mod_dir.is_dir():
            report.add(FAIL, f"enabled mod has no folder: {name}")
            continue
        for dll in sorted((mod_dir / "SKSE" / "Plugins").glob("*.dll")):
            report.add(PASS, f"plugin DLL: {dll.name}  <- {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runtime", default="all", help="1.5.97, 1.6.1170, 1.7.104 or all (default)")
    parser.add_argument("--profile", default=harness.DEV_PROFILE, help=f"MO2 profile name (default: {harness.DEV_PROFILE})")
    args = parser.parse_args()

    failed = False
    for runtime in harness.select_runtimes(args.runtime):
        print(f"== {runtime.name} / {args.profile}")
        report = Report()
        check_game(runtime, report)
        check_profile(runtime, args.profile, report)
        counts = report.counts
        result = FAIL if counts[FAIL] else WARN if counts[WARN] else PASS
        print(f"  => {result}  (pass {counts[PASS]}, warn {counts[WARN]}, fail {counts[FAIL]}, unknown {counts[UNKNOWN]})\n")
        failed = failed or counts[FAIL] > 0
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
