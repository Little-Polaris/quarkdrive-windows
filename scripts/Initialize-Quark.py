# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
"""Initialize a new machine or retain this machine's existing account."""
import argparse
import json
from pathlib import Path
import secrets
import subprocess
import time
import urllib.request
from Dependencies import applications

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "runtime"
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = "http://127.0.0.1:5244"


def api(path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token
    request = urllib.request.Request(BASE + path, headers=headers,
                                     data=json.dumps(data).encode() if data is not None else None)
    with HTTP.open(request, timeout=30) as response:
        result = json.load(response)
    if result["code"] != 200:
        # Avoid printing responses that might include credentials.
        raise RuntimeError(f"OpenList operation failed: {path}, code {result['code']}")
    return result["data"]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def initialize(drive, cookie_file):
    for folder in ("data", "logs", "temp", "cache", "services"):
        (RUNTIME / folder).mkdir(parents=True, exist_ok=True)
    apps = applications()
    exe = apps["openlist"]
    fresh = not (RUNTIME / "data/data.db").exists()
    if fresh:
        if not cookie_file or not cookie_file.exists():
            raise RuntimeError("A Quark browser Cookie is required on a new machine")
        config = {
            "force": False, "jwt_secret": secrets.token_urlsafe(32),
            "database": {"type": "sqlite3", "db_file": str(RUNTIME / "data/data.db"), "table_prefix": "x_"},
            "scheme": {"address": "127.0.0.1", "http_port": 5244, "https_port": -1},
            "temp_dir": str(RUNTIME / "temp"), "bleve_dir": str(RUNTIME / "data/bleve"),
            "log": {"enable": True, "name": str(RUNTIME / "logs/openlist.log"), "max_size": 10,
                    "max_backups": 3, "max_age": 7},
        }
        write_json(RUNTIME / "data/config.json", config)
        password = secrets.token_urlsafe(24)
        (RUNTIME / "admin-password.txt").write_text(password, encoding="utf-8")
        subprocess.run([str(exe), "admin", "set", password, "--data", str(RUNTIME / "data")],
                       cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    else:
        password = (RUNTIME / "admin-password.txt").read_text(encoding="utf-8-sig").strip()
        config = json.loads((RUNTIME / "data/config.json").read_text(encoding="utf-8-sig"))
        config["database"]["db_file"] = str(RUNTIME / "data/data.db")
        config["scheme"].update(address="127.0.0.1", http_port=5244, https_port=-1)
        config["temp_dir"] = str(RUNTIME / "temp")
        config["bleve_dir"] = str(RUNTIME / "data/bleve")
        config["log"]["name"] = str(RUNTIME / "logs/openlist.log")
        write_json(RUNTIME / "data/config.json", config)
    with (RUNTIME / "logs/setup-openlist.log").open("ab") as log:
        process = subprocess.Popen([str(exe), "server", "--data", str(RUNTIME / "data")], cwd=ROOT,
                                   stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for attempt in range(60):
                if process.poll() is not None:
                    raise RuntimeError("OpenList exited during configuration")
                try:
                    token = api("/api/auth/login", {"username": "admin", "password": password})["token"]
                    break
                except (OSError, RuntimeError):
                    if attempt == 59:
                        raise
                    time.sleep(0.5)
            (RUNTIME / "admin-token.txt").write_text(token, encoding="utf-8")
            storages = api("/api/admin/storage/list", token=token)["content"] or []
            matches = [s for s in storages if s["driver"] == "Quark" and s["mount_path"] == "/Quark"]
            if matches:
                storage = api(f"/api/admin/storage/get?id={matches[0]['id']}", token=token)
                if cookie_file and cookie_file.exists():
                    addition = json.loads(storage["addition"])
                    addition["cookie"] = cookie_file.read_text(encoding="utf-8-sig").strip()
                    storage["addition"] = json.dumps(addition)
                    api("/api/admin/storage/update", storage, token)
            else:
                if not cookie_file or not cookie_file.exists():
                    raise RuntimeError("A Quark browser Cookie is required to configure storage")
                storage = {"mount_path": "/Quark", "driver": "Quark", "order": 0,
                           "cache_expiration": 30, "web_proxy": True, "webdav_policy": "native_proxy",
                           "addition": json.dumps({"cookie": cookie_file.read_text(encoding="utf-8-sig").strip(),
                               "root_folder_id": "0", "order_by": "none", "order_direction": "asc",
                               "use_transcoding_address": False, "only_list_video_file": False})}
                api("/api/admin/storage/create", storage, token)
                storages = api("/api/admin/storage/list", token=token)["content"]
                storage = next(s for s in storages if s["mount_path"] == "/Quark" and s["driver"] == "Quark")
            # A non-working account must never be reported as installed successfully.
            api("/api/fs/list", {"path": "/Quark", "page": 1, "per_page": 1, "refresh": True}, token)
            if (RUNTIME / "webdav-account.json").exists():
                account = json.loads((RUNTIME / "webdav-account.json").read_text(encoding="utf-8-sig"))
            else:
                account = {"username": "quark_mount", "password": secrets.token_urlsafe(24)}
                write_json(RUNTIME / "webdav-account.json", account)
            users = api("/api/admin/user/list", token=token)["content"]
            if not any(u["username"] == account["username"] for u in users):
                api("/api/admin/user/create", {**account, "base_path": "/Quark", "permission": 1016,
                                              "role": 0, "disabled": False}, token)
            obscure = subprocess.check_output([apps["rclone"], "obscure", account["password"]],
                                               creationflags=subprocess.CREATE_NO_WINDOW, text=True).strip()
            (RUNTIME / "rclone.conf").write_text(
                "[quark]\ntype = webdav\nurl = http://127.0.0.1:5245/dav/\nvendor = other\n"
                f"user = {account['username']}\npass = {obscure}\n", encoding="utf-8")
            write_json(RUNTIME / "settings.json", {"drive_letter": drive, "storage_id": storage["id"], "applications": apps})
        finally:
            process.terminate()
            process.wait(timeout=20)
    if cookie_file and cookie_file.exists():
        cookie_file.unlink()
    print("Account and local configuration are ready.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--drive", default="Q", choices=list("KLMNOPQRSTUVWXYZ"))
    parser.add_argument("--cookie-file", type=Path)
    args = parser.parse_args()
    initialize(args.drive, args.cookie_file)
