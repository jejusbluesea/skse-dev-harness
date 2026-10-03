"""Removes the "[DEV] <Mod>" mod from each MO2 instance. Safe to re-run.

    python tools/undeploy.py --mod HelloSKSE
    python tools/undeploy.py --mod HelloSKSE --runtime 1.7.104

The mod is dropped from every profile's modlist.txt (backed up to
backups/<timestamp>/<runtime>/ first) and its folder is moved to the Recycle Bin.
An instance is skipped while its MO2 or game is running.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import harness

TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")


def recycle(folder: Path) -> bool:
    literal = str(folder).replace("'", "''")
    command = (
        "Add-Type -AssemblyName Microsoft.VisualBasic; "
        f"[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory('{literal}', 'OnlyErrorDialogs', 'SendToRecycleBin')"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, timeout=120)
    return not folder.exists()


def undeploy(runtime: harness.Runtime, mod: str) -> bool:
    name = harness.DEV_PREFIX + mod
    print(f"== {runtime.name}")
    busy = harness.is_instance_busy(runtime)
    if busy is None or busy:
        print("  [SKIP   ] MO2 or Skyrim of this runtime is running (or could not be checked); close it and re-run")
        return False

    for profile_dir in sorted((runtime.mo2_dir / "profiles").iterdir()):
        modlist = profile_dir / "modlist.txt"
        if not modlist.is_file():
            continue
        lines = modlist.read_text(encoding="utf-8").splitlines()
        kept = [line for line in lines if line not in (f"+{name}", f"-{name}")]
        if kept == lines:
            continue
        backup = harness.REPO_ROOT / "backups" / TIMESTAMP / runtime.name / profile_dir.name
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(modlist, backup / modlist.name)
        modlist.write_text("\r\n".join(kept) + "\r\n", encoding="utf-8", newline="")
        print(f"  removed from profile '{profile_dir.name}'")

    folder = runtime.mod_dir(name)
    if folder.is_dir():
        if not recycle(folder):
            print(f"  [FAIL   ] could not move to the Recycle Bin: {folder}")
            return False
        print(f"  moved to Recycle Bin: {folder}")
    print("  [PASS   ] not installed")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mod", required=True, help="mod name, without the [DEV] prefix")
    parser.add_argument("--runtime", default="all", help="1.5.97, 1.6.1170, 1.7.104 or all (default)")
    args = parser.parse_args()

    results = [undeploy(runtime, args.mod) for runtime in harness.select_runtimes(args.runtime)]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
