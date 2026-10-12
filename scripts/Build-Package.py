# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
"""Build a distributable archive using an explicit allowlist, never runtime/."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


def build():
    files = [ROOT / name for name in ("Deploy.ps1", "Install.cmd", "Uninstall.cmd", "README.md", "LICENSE",
                                     "THIRD_PARTY_NOTICES.md", "SECURITY.md", "CHANGELOG.md")]
    for folder in ("scripts", "docs", "bin"):
        files.extend(p for p in (ROOT / folder).rglob("*") if p.is_file()
                     and not any(part in p.relative_to(ROOT).parts for part in ("__pycache__", "local"))
                     and p.suffix not in (".pyc", ".log"))
    required = ["bin/openlist/openlist.exe", "bin/rclone/rclone.exe", "bin/winsw/WinSW.exe",
                "bin/python/python.exe", "bin/installers/winfsp.msi", "bin/python/LICENSE.txt",
                "bin/sources/OpenList-v4.2.6.tar.gz", "bin/sources/OpenList-Frontend-v4.2.6.tar.gz",
                "bin/sources/OpenList-v4.2.6-with-dependencies.tar.gz"]
    for name in required:
        if not (ROOT / name).is_file():
            raise RuntimeError(f"Missing bundled component: {name}; run Prepare-Bundle.py first")
    component_manifest = json.loads((ROOT / "docs/bundle-components.json").read_text(encoding="utf-8-sig"))
    source = component_manifest["generated_source"]
    if hashlib.sha256((ROOT / source["destination"]).read_bytes()).hexdigest() != source["sha256"]:
        raise RuntimeError("Corresponding source checksum mismatch")
    manifest = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    DIST.mkdir(exist_ok=True)
    archive = DIST / "QuarkDrive-Windows-x64.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(files):
            z.write(path, "QuarkDrive/" + path.relative_to(ROOT).as_posix())
        z.writestr("QuarkDrive/docs/package-sha256.json", json.dumps(manifest, indent=2))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert not any(any(part in Path(n).parts for part in ("runtime", ".git")) for n in z.namelist())
        assert "QuarkDrive/Install.cmd" in z.namelist()
        for name, expected in manifest.items():
            assert hashlib.sha256(z.read("QuarkDrive/" + name)).hexdigest() == expected, name
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (DIST / "QuarkDrive-Windows-x64.sha256.txt").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    update = DIST / "QuarkDrive-v0.2.1-update.zip"
    source_files = [path for path in files if path.relative_to(ROOT).parts[0] != "bin"]
    with zipfile.ZipFile(update, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(source_files):
            z.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(update) as z:
        assert z.testzip() is None
        assert not any(any(part in Path(name).parts for part in ("bin", "runtime", ".git")) for name in z.namelist())
    update_digest = hashlib.sha256(update.read_bytes()).hexdigest()
    (DIST / "QuarkDrive-v0.2.1-update.sha256.txt").write_text(f"{update_digest}  {update.name}\n", encoding="utf-8")
    print(json.dumps({"archive": str(archive), "bytes": archive.stat().st_size,
                      "files": len(manifest), "sha256": digest, "runtime_excluded": True,
                      "update_archive": str(update), "update_bytes": update.stat().st_size}, indent=2))


if __name__ == "__main__":
    build()
