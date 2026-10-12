# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
"""Regression coverage for Chinese Windows paths with UTF-8 mode disabled."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class UnicodeConfigurationTests(unittest.TestCase):
    def test_service_generation_preserves_chinese_paths(self):
        configuration = module("configuration", "Configure-Services.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "软件 空格" / "QuarkDriveMount"
            (root / "runtime").mkdir(parents=True)
            (root / "bin").mkdir()
            wrapper = root / "bin/WinSW.exe"
            wrapper.write_bytes(b"fixture wrapper, never executed")
            apps = {"winsw": str(wrapper), "openlist": str(root / "bin/openlist.exe"),
                    "python": str(root / "bin/python.exe")}
            (root / "runtime/settings.json").write_text(json.dumps({"applications": apps}, ensure_ascii=False), encoding="utf-8")
            with patch.object(configuration, "ROOT", root), patch.object(configuration, "SERVICES", root / "runtime/services"):
                configuration.configure()
            for service, executable in (("QuarkOpenList", apps["openlist"]), ("QuarkQuota", apps["python"])):
                xml = ET.parse(root / f"runtime/services/{service}.xml")
                self.assertEqual(xml.findtext("executable"), executable)
                self.assertEqual((root / f"runtime/services/{service}.exe").read_bytes(), wrapper.read_bytes())

    def test_quota_reads_settings_with_chinese_paths(self):
        quota = module("quota", "Quota-WebDAV.py")
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            (runtime / "admin-token.txt").write_text("fixture-token", encoding="utf-8")
            (runtime / "settings.json").write_text(json.dumps({"storage_id": 1, "applications": {
                "python": "C:\\软件\\QuarkDriveMount\\bin\\python\\python.exe"}}, ensure_ascii=False), encoding="utf-8")
            storage = {"code": 200, "data": {"driver": "Quark", "addition": json.dumps({"cookie": "fixture-cookie"})}}
            member = {"code": 0, "data": {"total_capacity": 1000, "use_capacity": 250}}
            with patch.object(quota, "RUNTIME", runtime), \
                 patch.object(quota.local_http, "open", return_value=io.BytesIO(json.dumps(storage).encode())), \
                 patch.object(quota.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(member).encode())):
                self.assertEqual(quota.get_quota(), {"total": 1000, "used": 250, "free": 750})


if __name__ == "__main__":
    unittest.main()
