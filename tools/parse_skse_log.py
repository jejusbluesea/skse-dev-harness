"""Summarises the SKSE logs of the most recent game launch.

All three runtimes write to the same Documents folder, so run this right after
each launch, before starting another runtime.

    python tools/parse_skse_log.py                    # summarise
    python tools/parse_skse_log.py --expect HelloSKSE # FAIL unless HelloSKSE loaded
    python tools/parse_skse_log.py --expect HelloSKSE --save

--save keeps the result under test-results/<runtime>/<launch time>.json.
Exit code is 1 if any check FAILs.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import re
import sys
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

import harness
from harness import FAIL, PASS, UNKNOWN, WARN

HEADER_RE = re.compile(r"SKSE64 runtime: initialize \(version = (\S+) ([0-9A-Fa-f]{8})")
PLUGIN_RE = re.compile(r"^plugin (?P<path>.+?\.dll) \((?P<info>[^)]*)\) (?P<status>.+?)(?: \(handle (?P<handle>\d+)\))?$")
LOAD_ERROR_RE = re.compile(r"couldn't load plugin|LoadLibrary failed|not a valid dll", re.IGNORECASE)
PROBLEM_RE = re.compile(r"\[(error|critical|warning|warn)\]", re.IGNORECASE)
# Tags our own dev plugins write, e.g. "[load] OK", "[lifecycle] kDataLoaded".
MARKER_RE = re.compile(r"\[(load|lifecycle|addrlib|hello)\] .*")
ADDRESS_LIBRARY_RE = re.compile(r"address library|versionlib|version-\d", re.IGNORECASE)
# A plugin log older than the launch by more than this is a leftover from a previous run.
STALE_SECONDS = 120


def documents_dir() -> Path:
    buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer)  # CSIDL_PERSONAL
    return Path(buffer.value)


def default_log_dir() -> Path:
    return documents_dir() / "My Games" / "Skyrim Special Edition" / "SKSE"


def unpack_runtime(packed: int) -> str:
    return f"{packed >> 24}.{(packed >> 16) & 0xFF}.{(packed >> 4) & 0xFFF}.{packed & 0xF}"


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def parse_skse_log(path: Path) -> dict:
    result = {"skse": None, "runtime": None, "plugins": [], "load_errors": [], "messages": []}
    for line in read_lines(path):
        line = line.strip()
        if header := HEADER_RE.search(line):
            result["skse"] = header.group(1)
            result["runtime"] = unpack_runtime(int(header.group(2), 16))
        elif plugin := PLUGIN_RE.match(line):
            status = plugin.group("status")
            result["plugins"].append({
                "name": Path(plugin.group("path").replace("\\", "/")).stem,
                "status": status,
                "loaded": status == "loaded correctly",
            })
        elif LOAD_ERROR_RE.search(line):
            result["load_errors"].append(line)
        elif message := re.match(r"dispatch message \((\d+)\)", line):
            result["messages"].append(int(message.group(1)))
    return result


def parse_plugin_log(path: Path) -> dict:
    lines = read_lines(path)
    return {
        "problems": [line for line in lines if PROBLEM_RE.search(line)],
        "markers": [m.group(0) for line in lines if (m := MARKER_RE.search(line))],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log-dir", type=Path, default=None, help="SKSE log folder (default: Documents\\My Games\\Skyrim Special Edition\\SKSE)")
    parser.add_argument("--expect", action="append", default=[], metavar="PLUGIN", help="plugin that must have loaded (repeatable)")
    parser.add_argument("--save", action="store_true", help="keep the result under test-results/<runtime>/")
    args = parser.parse_args()

    log_dir = args.log_dir or default_log_dir()
    skse_log = log_dir / "skse64.log"
    checks: list[tuple[str, str]] = []

    def add(status: str, message: str) -> None:
        checks.append((status, message))
        print(f"  [{status:<7}] {message}")

    print(f"== {skse_log}")
    if not skse_log.is_file():
        add(UNKNOWN, "skse64.log not found; launch the game through skse64_loader first")
        return 0

    launched = skse_log.stat().st_mtime
    skse = parse_skse_log(skse_log)
    print(f"  launch: {datetime.fromtimestamp(launched):%Y-%m-%d %H:%M:%S}")

    if skse["runtime"] is None:
        add(UNKNOWN, "SKSE header line not found; runtime could not be determined")
    else:
        add(PASS, f"runtime {skse['runtime']}, SKSE {skse['skse']}")
        runtime = harness.RUNTIMES.get(skse["runtime"].rsplit(".", 1)[0])
        if runtime is None:
            add(WARN, "this runtime is not one of the configured test runtimes")
        elif runtime.skse != skse["skse"]:
            add(FAIL, f"SKSE {skse['skse']} does not match the expected {runtime.skse}")

    if "init complete" not in skse_log.read_text(encoding="utf-8", errors="replace"):
        add(FAIL, "SKSE did not reach 'init complete'")
    # Message 8 is kDataLoaded: the game reached the main menu.
    add(PASS if 8 in skse["messages"] else WARN,
        "main menu reached (kDataLoaded dispatched)" if 8 in skse["messages"] else "kDataLoaded was not dispatched (game closed before the main menu?)")

    for plugin in skse["plugins"]:
        add(PASS if plugin["loaded"] else FAIL, f"plugin {plugin['name']}: {plugin['status']}")
        if not plugin["loaded"] and ADDRESS_LIBRARY_RE.search(plugin["status"]):
            add(FAIL, f"plugin {plugin['name']}: Address Library problem")
    for line in skse["load_errors"]:
        add(FAIL, line)
    if not skse["plugins"] and not skse["load_errors"]:
        add(PASS, "no plugins were scanned")

    loaded = {p["name"].lower() for p in skse["plugins"] if p["loaded"]}
    for expected in args.expect:
        if expected.lower() not in loaded:
            add(FAIL, f"expected plugin did not load: {expected}")

    plugin_logs = {}
    for path in sorted(log_dir.glob("*.log")):
        if path.name.lower().startswith("skse64"):
            continue
        if path.stat().st_mtime < launched - STALE_SECONDS:
            add(WARN, f"{path.name} is older than this launch; ignored")
            continue
        parsed = parse_plugin_log(path)
        plugin_logs[path.stem] = parsed
        print(f"  -- {path.name}")
        for marker in parsed["markers"]:
            print(f"       {marker}")
        for line in parsed["problems"]:
            is_address_library = bool(ADDRESS_LIBRARY_RE.search(line))
            is_warning = re.search(r"\[warn", line, re.IGNORECASE) and not is_address_library
            add(WARN if is_warning else FAIL, f"{path.name}: {line.strip()}")
        if not parsed["problems"]:
            add(PASS, f"{path.name}: no errors or warnings")
    for expected in args.expect:
        if expected not in plugin_logs:
            add(FAIL, f"expected plugin wrote no log: {expected}.log")

    statuses = [status for status, _ in checks]
    result = FAIL if FAIL in statuses else WARN if WARN in statuses else PASS
    print(f"  => {result}")

    if args.save:
        folder = (skse["runtime"] or "unknown").rsplit(".", 1)[0] if skse["runtime"] else "unknown"
        out = harness.REPO_ROOT / "test-results" / folder / f"{datetime.fromtimestamp(launched):%Y%m%d-%H%M%S}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "launch": datetime.fromtimestamp(launched).isoformat(timespec="seconds"),
            "result": result,
            "skse": skse,
            "plugin_logs": plugin_logs,
            "checks": [{"status": status, "message": message} for status, message in checks],
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  saved: {out.relative_to(harness.REPO_ROOT)}")

    return 1 if result == FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
