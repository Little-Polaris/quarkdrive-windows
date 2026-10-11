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
    files = [ROOT / name for name in ("Install.cmd", "Uninstall.cmd", "README.md", "LICENSE",
                                     "THIRD_PARTY_NOTICES.md", "SECURITY.md", "CHANGELOG.md")]
    for folder in ("scripts", "docs"):
        files.extend(p for p in (ROOT / folder).rglob("*") if p.is_file()
                     and not any(part in p.relative_to(ROOT).parts for part in ("__pycache__", "licenses", "local"))
                     and p.suffix not in (".pyc", ".log"))
    manifest = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    DIST.mkdir(exist_ok=True)
    archive = DIST / "QuarkDrive-Windows-x64.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(files):
            z.write(path, "QuarkDrive/" + path.relative_to(ROOT).as_posix())
        z.writestr("QuarkDrive/docs/package-sha256.json", json.dumps(manifest, indent=2))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert not any(any(part in Path(n).parts for part in ("runtime", ".git", "bin", "licenses")) for n in z.namelist())
        assert "QuarkDrive/Install.cmd" in z.namelist()
        for name, expected in manifest.items():
            assert hashlib.sha256(z.read("QuarkDrive/" + name)).hexdigest() == expected, name
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (DIST / "QuarkDrive-Windows-x64.sha256.txt").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(json.dumps({"archive": str(archive), "bytes": archive.stat().st_size,
                      "files": len(manifest), "sha256": digest, "runtime_excluded": True}, indent=2))


if __name__ == "__main__":
    build()
