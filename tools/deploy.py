"""Copies a staged build (mods/<Mod>/dist/) into the "[DEV] <Mod>" mod of each MO2 instance.

    python tools/deploy.py                     # HelloSKSE -> all runtimes
    python tools/deploy.py --mod HelloSKSE --runtime 1.7.104

Only the mod folder is written. Enabling the mod in a profile is done by
tools/setup_profiles.py (or by hand in MO2).
"""

from __future__ import annotations

import argparse
import shutil
import sys

import harness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mod", default="HelloSKSE", help="mod name under mods/ (default: HelloSKSE)")
    parser.add_argument("--runtime", default="all", help="1.5.97, 1.6.1170, 1.7.104 or all (default)")
    args = parser.parse_args()

    stage = harness.REPO_ROOT / "mods" / args.mod / "dist"
    files = [p for p in stage.rglob("*") if p.is_file()] if stage.is_dir() else []
    if not files:
        sys.exit(f"nothing staged in {stage}; run tools/build.ps1 first")

    failed = False
    for runtime in harness.select_runtimes(args.runtime):
        target = runtime.mod_dir(harness.DEV_PREFIX + args.mod)
        print(f"== {runtime.name}: {target}")
        if not runtime.mo2_dir.is_dir():
            print("  [FAIL   ] MO2 instance not found")
            failed = True
            continue
        try:
            for source in files:
                destination = target / source.relative_to(stage)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                print(f"  [PASS   ] {source.relative_to(stage)}")
        except PermissionError as error:
            print(f"  [FAIL   ] {error} (is the game still running?)")
            failed = True
            continue
        if harness.is_instance_busy(runtime):
            print("  [WARN   ] MO2 is running: press F5 in MO2 to refresh the mod list")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
