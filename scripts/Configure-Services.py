# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
"""Generate path-independent WinSW configurations, containing no credentials."""
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import json

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ROOT / "runtime/services"


def configure():
    SERVICES.mkdir(parents=True, exist_ok=True)
    apps = json.loads((ROOT / "runtime/settings.json").read_text(encoding="utf-8-sig"))["applications"]
    specs = [
        ("QuarkOpenList", "Quark - OpenList", apps["openlist"],
         r'server --data "%BASE%\..\data"', []),
        ("QuarkQuota", "Quark - Capacity WebDAV", apps["python"],
         r'-u "%BASE%\..\..\scripts\Quota-WebDAV.py"', ["QuarkOpenList"]),
        ("QuarkMount", "Quark - Network Drive", r"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe",
         r'-NoProfile -ExecutionPolicy Bypass -File "%BASE%\..\..\scripts\Run-Mount.ps1"', ["QuarkQuota"]),
    ]
    for service_id, name, executable, arguments, dependencies in specs:
        shutil.copy2(apps["winsw"], SERVICES / f"{service_id}.exe")
        xml = ET.Element("service")
        for key, value in {
            "id": service_id, "name": name, "description": "Local Quark drive; automatic start and failure recovery.",
            "executable": executable, "arguments": arguments, "workingdirectory": r"%BASE%\..\..",
            "startmode": "Automatic", "delayedAutoStart": "false", "stoptimeout": "30sec",
            "logpath": r"%BASE%\..\logs", "resetfailure": "1day",
        }.items():
            ET.SubElement(xml, key).text = value
        for dependency in dependencies:
            ET.SubElement(xml, "depend").text = dependency
        for delay in ("5sec", "15sec", "60sec"):
            ET.SubElement(xml, "onfailure", action="restart", delay=delay)
        log = ET.SubElement(xml, "log", mode="roll-by-size")
        ET.SubElement(log, "sizeThreshold").text = "10240"
        ET.SubElement(log, "keepFiles").text = "3"
        ET.indent(xml)
        ET.ElementTree(xml).write(SERVICES / f"{service_id}.xml", encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    configure()
