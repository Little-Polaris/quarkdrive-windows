# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
"""Resolve bundled applications, with explicit service paths."""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent


def program(name):
    candidates = {
        "openlist": ROOT / "bin/openlist/openlist.exe",
        "rclone": ROOT / "bin/rclone/rclone.exe",
        "winsw": ROOT / "bin/winsw/WinSW.exe",
    }
    local = candidates[name]
    found = local if local.is_file() else shutil.which({"winsw": "WinSW.exe"}.get(name, name))
    if not found:
        raise RuntimeError(f"Missing {name}. See docs/dependencies.md for installation and file locations.")
    return str(Path(found).resolve())


def applications():
    if sys.maxsize <= 2**32:
        raise RuntimeError("64-bit Python is required")
    return {"python": sys.executable, **{name: program(name) for name in ("openlist", "rclone", "winsw")}}
