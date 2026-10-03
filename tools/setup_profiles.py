"""Brings the MO2 profiles of each instance to the harness layout. Safe to re-run.

    01 - SKSE        -> Address Library enabled, renamed to "01 - SKSE Base" (baseline)
    02 - Dev Sanity  -> copy of the baseline with the given [DEV] mods enabled

    python tools/setup_profiles.py --dev-mod HelloSKSE
    python tools/setup_profiles.py --runtime 1.5.97 --dev-mod HelloSKSE

An instance is skipped while its MO2 or game is running. Profile files are
backed up to backups/<timestamp>/<runtime>/ before the first change.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

import harness

TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")


def backup(runtime: harness.Runtime, profile_dir: Path) -> None:
    target = harness.REPO_ROOT / "backups" / TIMESTAMP / runtime.name / profile_dir.name
    if target.exists():
        return
    target.mkdir(parents=True)
    for path in profile_dir.iterdir():
        if path.is_file():
            shutil.copy2(path, target / path.name)
    print(f"  backup: {target.relative_to(harness.REPO_ROOT)}")


def set_mods_enabled(runtime: harness.Runtime, profile_dir: Path, names: list[str]) -> None:
    """Enables the named mods in modlist.txt, adding missing ones at the highest priority."""
    modlist = profile_dir / "modlist.txt"
    lines = modlist.read_text(encoding="utf-8").splitlines()
    changed = False
    for name in names:
        if f"+{name}" in lines:
            continue
        if f"-{name}" in lines:
            lines[lines.index(f"-{name}")] = f"+{name}"
        else:
            first_mod = next((i for i, line in enumerate(lines) if not line.startswith("#")), len(lines))
            lines.insert(first_mod, f"+{name}")
        changed = True
        print(f"  enabled in '{profile_dir.name}': {name}")
    if changed:
        backup(runtime, profile_dir)
        modlist.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")


def select_profile(runtime: harness.Runtime, profile: str) -> None:
    ini = runtime.mo2_dir / "ModOrganizer.ini"
    text = ini.read_text(encoding="utf-8")
    lines = text.splitlines()
    wanted = f"selected_profile=@ByteArray({profile})"
    for index, line in enumerate(lines):
        if line.startswith("selected_profile=") and line != wanted:
            target = harness.REPO_ROOT / "backups" / TIMESTAMP / runtime.name
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ini, target / ini.name)
            lines[index] = wanted
            newline = "\r\n" if "\r\n" in ini.read_bytes().decode("utf-8") else "\n"
            ini.write_text(newline.join(lines) + newline, encoding="utf-8", newline="")
            print(f"  selected profile: {profile}")


def setup(runtime: harness.Runtime, dev_mods: list[str]) -> bool:
    print(f"== {runtime.name}")
    busy = harness.is_instance_busy(runtime)
    if busy is None or busy:
        print("  [SKIP   ] MO2 or Skyrim of this runtime is running (or could not be checked); close it and re-run")
        return False

    base = runtime.profile_dir(harness.BASE_PROFILE)
    legacy = runtime.profile_dir(harness.LEGACY_BASE_PROFILE)
    if not base.is_dir():
        if not legacy.is_dir():
            print(f"  [FAIL   ] neither '{harness.LEGACY_BASE_PROFILE}' nor '{harness.BASE_PROFILE}' exists")
            return False
        set_mods_enabled(runtime, legacy, [harness.ADDRESS_LIBRARY_MOD])
        legacy.rename(base)
        print(f"  renamed profile: '{legacy.name}' -> '{base.name}'")
    else:
        set_mods_enabled(runtime, base, [harness.ADDRESS_LIBRARY_MOD])

    dev = runtime.profile_dir(harness.DEV_PROFILE)
    if not dev.is_dir():
        shutil.copytree(base, dev)
        print(f"  created profile: '{dev.name}' (copy of '{base.name}')")

    dev_names = [harness.DEV_PREFIX + mod for mod in dev_mods]
    for name in dev_names:
        if not runtime.mod_dir(name).is_dir():
            print(f"  [FAIL   ] mod folder missing: {name} (run tools/deploy.py first)")
            return False
    set_mods_enabled(runtime, dev, dev_names)
    select_profile(runtime, harness.DEV_PROFILE)
    print("  [PASS   ] profiles ready")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runtime", default="all", help="1.5.97, 1.6.1170, 1.7.104 or all (default)")
    parser.add_argument("--dev-mod", action="append", default=[], metavar="MOD", help="[DEV] mod to enable in the dev profile (repeatable)")
    args = parser.parse_args()

    results = [setup(runtime, args.dev_mod) for runtime in harness.select_runtimes(args.runtime)]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
