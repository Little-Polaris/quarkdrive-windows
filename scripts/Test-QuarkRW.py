# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
"""Exercise only a fresh, uniquely named test folder on the mounted drive."""
import base64
import ctypes
import datetime
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid

root = Path(__file__).resolve().parent.parent
runtime = root / "runtime"
base = "http://127.0.0.1:5244"
token = (runtime / "admin-token.txt").read_text(encoding="utf-8-sig").strip()
http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
settings_file = runtime / "settings.json"
drive_letter = json.loads(settings_file.read_text(encoding="utf-8-sig"))["drive_letter"] if settings_file.exists() else "Q"
drive_root = Path(drive_letter + ":/")
account = json.loads((runtime / "webdav-account.json").read_text(encoding="utf-8-sig"))
basic = base64.b64encode(
    (account["username"] + ":" + account["password"]).encode()
).decode()
folder_name = "__codex_mount_test_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
folder = drive_root / folder_name
original = folder / "read-write-test.txt"
renamed = folder / "renamed-test.txt"
assert folder.parent == drive_root and not folder.exists()


def cloud_list(path):
    global token
    request = urllib.request.Request(
        base + "/api/fs/list",
        data=json.dumps({"path": path, "page": 1, "per_page": 100, "refresh": True}).encode(),
        headers={"Authorization": token, "Content-Type": "application/json"},
    )
    response = json.load(http.open(request, timeout=15))
    if response["code"] == 401:
        login_request = urllib.request.Request(base + "/api/auth/login", data=json.dumps({"username": "admin",
            "password": (runtime / "admin-password.txt").read_text(encoding="utf-8-sig").strip()}).encode(),
            headers={"Content-Type": "application/json"})
        login = json.load(http.open(login_request, timeout=15))
        if login["code"] != 200:
            raise RuntimeError("OpenList sign-in failed")
        token = login["data"]["token"]
        (runtime / "admin-token.txt").write_text(token, encoding="utf-8")
        request.add_header("Authorization", token)
        response = json.load(http.open(request, timeout=15))
    if response["code"] != 200:
        raise RuntimeError("Cloud listing failed: " + str(response["code"]))
    return response["data"]["content"] or []


def wait_for_content(name, expected):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            cloud_list("/Quark/" + folder_name)
            request = urllib.request.Request(
                base + "/dav/" + folder_name + "/" + name,
                headers={"Authorization": "Basic " + basic},
            )
            with http.open(request, timeout=15) as response:
                actual = response.read(len(expected) + 1)
            if actual == expected:
                return
        except (urllib.error.URLError, TimeoutError, RuntimeError):
            pass
        time.sleep(2)
    raise RuntimeError("Cloud content did not match within 60 seconds.")


created = False
result = {"drive": drive_letter + ":", "mode": "read/write", "driver": "Quark", "test_folder": folder_name}
try:
    folder.mkdir()
    created = True
    print("Created isolated test folder.", flush=True)
    first = ("Codex Quark mount upload test " + uuid.uuid4().hex + "\n").encode() * 16
    original.write_bytes(first)
    wait_for_content(original.name, first)
    result["upload_cloud_verified"] = True
    print("Upload verified from cloud, beyond local cache.", flush=True)

    second = first + b"Verified edit saved through mounted drive.\n"
    original.write_bytes(second)
    wait_for_content(original.name, second)
    result["edit_cloud_verified"] = True
    print("Edited contents verified from cloud.", flush=True)

    original.rename(renamed)
    wait_for_content(renamed.name, second)
    result["rename_cloud_verified"] = True
    print("Rename verified from cloud.", flush=True)
    assert renamed.read_bytes() == second
    result["drive_read_verified"] = True
finally:
    if created:
        for file in (original, renamed):
            if file.exists():
                file.unlink()
        folder.rmdir()

deadline = time.monotonic() + 45
while any(item["name"] == folder_name for item in cloud_list("/Quark")):
    if time.monotonic() >= deadline:
        raise RuntimeError("Test folder deletion has not reached the cloud.")
    time.sleep(2)
result["delete_cloud_verified"] = True
result["network_drive_type"] = ctypes.windll.kernel32.GetDriveTypeW(drive_letter + ":\\")
assert result["network_drive_type"] == 4
(runtime / "verification-rw.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print("Delete verified from cloud; test folder cleaned up. All read/write checks passed.", flush=True)
