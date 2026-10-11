# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Little-Polaris
"""Add Quark quota properties to the existing local OpenList WebDAV service."""
import base64
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

RUNTIME = Path(__file__).resolve().parent.parent / "runtime"
OPENLIST = "http://127.0.0.1:5244"
HOP_HEADERS = {"connection", "proxy-connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade"}
ET.register_namespace("D", "DAV:")
quota_lock = threading.Lock()
quota_cache = None
quota_time = 0
local_http = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get_quota():
    global quota_cache, quota_time
    with quota_lock:
        if quota_cache is not None and time.monotonic() - quota_time < 60:
            return quota_cache
        token = (RUNTIME / "admin-token.txt").read_text().strip()
        settings_file = RUNTIME / "settings.json"
        storage_id = json.loads(settings_file.read_text())["storage_id"] if settings_file.exists() else 2
        request = urllib.request.Request(
            OPENLIST + f"/api/admin/storage/get?id={storage_id}", headers={"Authorization": token}
        )
        with local_http.open(request, timeout=5) as response:
            storage = json.load(response)
        if storage["code"] == 401:
            request = urllib.request.Request(
                OPENLIST + "/api/auth/login",
                data=json.dumps({"username": "admin", "password": (RUNTIME / "admin-password.txt").read_text().strip()}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with local_http.open(request, timeout=5) as response:
                login = json.load(response)
            if login["code"] != 200:
                raise RuntimeError("OpenList sign-in failed")
            token = login["data"]["token"]
            (RUNTIME / "admin-token.txt").write_text(token, encoding="utf-8")
            request = urllib.request.Request(
                OPENLIST + f"/api/admin/storage/get?id={storage_id}", headers={"Authorization": token}
            )
            with local_http.open(request, timeout=5) as response:
                storage = json.load(response)
        if storage["code"] != 200 or storage["data"]["driver"] != "Quark":
            raise RuntimeError("Quark storage is unavailable")
        cookie = json.loads(storage["data"]["addition"])["cookie"]
        request = urllib.request.Request(
            "https://drive.quark.cn/1/clouddrive/member?pr=ucpro&fr=pc"
            "&fetch_subscribe=false&_ch=home&fetch_identity=false",
            headers={"Cookie": cookie, "Referer": "https://pan.quark.cn", "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            member = json.load(response)
        if member.get("code") != 0:
            raise RuntimeError("Quark quota request failed")
        data = member["data"]
        total, used = int(data["total_capacity"]), int(data["use_capacity"])
        if not 0 <= used <= total:
            raise RuntimeError("Invalid Quark quota response")
        quota_cache = {"total": total, "used": used, "free": total - used}
        quota_time = time.monotonic()
        (RUNTIME / "quota.json").write_text(json.dumps(quota_cache, indent=2), encoding="utf-8")
        return quota_cache


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def send_body(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        self.close_connection = True

    def quota_response(self):
        try:
            quota = get_quota()
        except Exception:
            self.send_body(503, b"Quark quota is temporarily unavailable", "text/plain")
            return
        multistatus = ET.Element("{DAV:}multistatus")
        response = ET.SubElement(multistatus, "{DAV:}response")
        ET.SubElement(response, "{DAV:}href").text = "/dav/"
        propstat = ET.SubElement(response, "{DAV:}propstat")
        prop = ET.SubElement(propstat, "{DAV:}prop")
        ET.SubElement(prop, "{DAV:}quota-available-bytes").text = str(quota["free"])
        ET.SubElement(prop, "{DAV:}quota-used-bytes").text = str(quota["used"])
        ET.SubElement(propstat, "{DAV:}status").text = "HTTP/1.1 200 OK"
        self.send_body(207, ET.tostring(multistatus, encoding="utf-8", xml_declaration=True), "application/xml")

    def forward(self):
        path = urllib.parse.urlsplit(self.path).path
        if path != "/dav" and not path.startswith("/dav/"):
            self.send_body(404, b"Not found", "text/plain")
            return
        account = json.loads((RUNTIME / "webdav-account.json").read_text())
        expected = "Basic " + base64.b64encode(
            (account["username"] + ":" + account["password"]).encode()
        ).decode()
        if not hmac.compare_digest(self.headers.get("Authorization", ""), expected):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Quark WebDAV"')
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            return
        body = None
        if self.command == "PROPFIND":
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1048576:
                self.send_body(413, b"Request too large", "text/plain")
                return
            body = self.rfile.read(length)
            if path.rstrip("/") == "/dav" and body:
                try:
                    props = ET.fromstring(body).find("{DAV:}prop")
                    names = {item.tag for item in props} if props is not None else set()
                    quota_names = {"{DAV:}quota-available-bytes", "{DAV:}quota-used-bytes"}
                    if names and names <= quota_names:
                        self.quota_response()
                        return
                except ET.ParseError:
                    pass
        connection = http.client.HTTPConnection("127.0.0.1", 5244, timeout=120)
        try:
            connection.putrequest(self.command, self.path, skip_host=True, skip_accept_encoding=True)
            for name, value in self.headers.items():
                if name.lower() not in HOP_HEADERS | {"host", "expect"}:
                    # Rclone's COPY/MOVE destinations must address the upstream service.
                    if name.lower() == "destination":
                        value = value.replace("http://127.0.0.1:5245/", OPENLIST + "/", 1)
                    connection.putheader(name, value)
            connection.putheader("Host", "127.0.0.1:5244")
            connection.putheader("Connection", "close")
            chunked = self.headers.get("Transfer-Encoding", "").lower() == "chunked"
            if chunked and body is None:
                connection.putheader("Transfer-Encoding", "chunked")
            connection.endheaders()
            if body is not None:
                connection.send(body)
            elif chunked:
                while True:
                    size = int(self.rfile.readline().split(b";", 1)[0], 16)
                    if size == 0:
                        while self.rfile.readline() not in (b"\r\n", b"\n", b""):
                            pass
                        connection.send(b"0\r\n\r\n")
                        break
                    remaining = size
                    connection.send(f"{size:x}\r\n".encode())
                    while remaining:
                        block = self.rfile.read(min(1048576, remaining))
                        if not block:
                            raise EOFError("Incomplete request")
                        connection.send(block)
                        remaining -= len(block)
                    if self.rfile.read(2) != b"\r\n":
                        raise ValueError("Invalid chunk boundary")
                    connection.send(b"\r\n")
            else:
                remaining = int(self.headers.get("Content-Length", "0"))
                while remaining:
                    block = self.rfile.read(min(1048576, remaining))
                    if not block:
                        raise EOFError("Incomplete request")
                    connection.send(block)
                    remaining -= len(block)
            response = connection.getresponse()
            self.send_response(response.status)
            for name, value in response.getheaders():
                if name.lower() not in HOP_HEADERS:
                    self.send_header(name, value)
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD":
                while block := response.read(1048576):
                    self.wfile.write(block)
            self.close_connection = True
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        finally:
            connection.close()

    do_GET = do_HEAD = do_PROPFIND = do_PUT = do_DELETE = do_MKCOL = do_MOVE = do_COPY = do_PROPPATCH = do_OPTIONS = do_LOCK = do_UNLOCK = forward


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 5245), Handler)
    server.daemon_threads = True
    print("Local quota-aware WebDAV ready on 127.0.0.1:5245", flush=True)
    server.serve_forever()
