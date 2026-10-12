# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
"""Prepare pinned official components for a self-contained Release archive."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import os
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def prepare(cache, proxy, go):
    manifest = json.loads((ROOT / "docs/bundle-components.json").read_text(encoding="utf-8"))
    http = urllib.request.build_opener(urllib.request.ProxyHandler({"https": proxy, "http": proxy})) if proxy else urllib.request.build_opener()
    downloads = ROOT / "runtime/downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    for component in manifest["components"]:
        target = ROOT / component["destination"]
        target.parent.mkdir(parents=True, exist_ok=True)
        cached = cache / component["destination"].removeprefix("bin/") if cache else None
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == component["sha256"]:
            continue
        if cached and cached.is_file() and hashlib.sha256(cached.read_bytes()).hexdigest() == component["sha256"]:
            shutil.copy2(cached, target)
        else:
            download = downloads / component["url"].rsplit("/", 1)[-1]
            if not download.exists():
                with http.open(component["url"], timeout=120) as response:
                    download.write_bytes(response.read())
            payload = download.read_bytes()
            if component.get("archive_sha256") and hashlib.sha256(payload).hexdigest() != component["archive_sha256"]:
                raise RuntimeError(f"Archive checksum mismatch: {download.name}")
            if component.get("archive_member"):
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    names = [name for name in archive.namelist() if Path(name).name == component["archive_member"]]
                    if len(names) != 1:
                        raise RuntimeError("Unexpected upstream archive layout")
                    target.write_bytes(archive.read(names[0]))
            else:
                target.write_bytes(payload)
        if hashlib.sha256(target.read_bytes()).hexdigest() != component["sha256"]:
            raise RuntimeError(f"Component checksum mismatch: {target.name}")
    python_root = ROOT / "bin/python"
    python_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ROOT / "bin/installers/python-3.14.6-embed-amd64.zip") as archive:
        for item in archive.infolist():
            target = (python_root / item.filename).resolve()
            if not target.is_relative_to(python_root.resolve()):
                raise RuntimeError("Invalid Python archive path")
        archive.extractall(python_root)
    # Isolated Python needs an explicit path for this project's sibling modules.
    (python_root / "python314._pth").write_text("python314.zip\n.\n../../scripts\n", encoding="utf-8")
    complete = ROOT / "bin/sources/OpenList-v4.2.6-with-dependencies.tar.gz"
    saved = manifest.get("generated_source", {})
    if not complete.exists() or hashlib.sha256(complete.read_bytes()).hexdigest() != saved.get("sha256"):
        go = go or shutil.which("go")
        if not go:
            raise RuntimeError("Go 1.27 is required by maintainers to bundle the corresponding source; pass --go path/to/go.exe")
        with tempfile.TemporaryDirectory(prefix="source-build-", dir=ROOT / "runtime") as folder:
            build_root = Path(folder).resolve()
            assert build_root.parent == (ROOT / "runtime").resolve()
            with tarfile.open(ROOT / "bin/sources/OpenList-v4.2.6.tar.gz") as archive:
                archive.extractall(build_root, filter="data")
            source = build_root / "OpenList-4.2.6"
            env = os.environ.copy()
            env["GOTOOLCHAIN"] = "local"
            if proxy:
                env.update(HTTPS_PROXY=proxy, HTTP_PROXY=proxy)
            subprocess.run([str(go), "mod", "vendor"], cwd=source, env=env, check=True)
            with tarfile.open(complete, "w:gz") as archive:
                archive.add(source, arcname="OpenList-4.2.6")
        manifest["generated_source"] = {"destination": complete.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(complete.read_bytes()).hexdigest(),
            "method": "Upstream v4.2.6 source plus go mod vendor using locked go.sum dependencies"}
        (ROOT / "docs/bundle-components.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Official applications, runtime, installers, notices and sources are ready.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, help="Optional existing bin/ folder containing verified components")
    parser.add_argument("--proxy", help="Optional proxy used only while preparing a Release")
    parser.add_argument("--go", help="Go executable used by maintainers to bundle dependency source")
    args = parser.parse_args()
    prepare(args.cache, args.proxy, args.go)
