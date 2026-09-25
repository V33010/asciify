from __future__ import annotations

import http.client
import socketserver
import threading
from pathlib import Path

from ascii_art import server


def run_test_server():
    server.SERVER_STATE["current_file"] = None
    httpd = socketserver.TCPServer(("127.0.0.1", 0), server.DynamicFileHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


def test_dynamic_file_handler_serves_current_file(tmp_path):
    target = tmp_path / "art.txt"
    target.write_text("hello\nworld\n", encoding="utf-8")
    httpd, thread = run_test_server()
    server.SERVER_STATE["current_file"] = target
    try:
        conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=2)
        conn.request("GET", "/myfile")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        conn.close()

        assert response.status == 200
        assert body == "hello\nworld\n"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
        server.SERVER_STATE["current_file"] = None


def test_dynamic_file_handler_accepts_root_path(tmp_path):
    target = tmp_path / "art.txt"
    target.write_text("root", encoding="utf-8")
    httpd, thread = run_test_server()
    server.SERVER_STATE["current_file"] = target
    try:
        conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=2)
        conn.request("GET", "/")
        response = conn.getresponse()
        assert response.status == 200
        assert response.read().decode() == "root"
        conn.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
        server.SERVER_STATE["current_file"] = None


def test_dynamic_file_handler_returns_404_without_current_file():
    server.SERVER_STATE["current_file"] = None
    httpd, thread = run_test_server()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=2)
        conn.request("GET", "/myfile")
        response = conn.getresponse()
        response.read()
        conn.close()
        assert response.status == 404
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_dynamic_file_handler_rejects_unknown_path():
    httpd, thread = run_test_server()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=2)
        conn.request("GET", "/unknown")
        response = conn.getresponse()
        response.read()
        conn.close()
        assert response.status == 404
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_open_browser_falls_back_to_webbrowser(monkeypatch):
    calls = []
    monkeypatch.setattr(server.shutil, "which", lambda name: None)
    monkeypatch.setattr(server.webbrowser, "open", lambda url: calls.append(url))

    server.open_browser_silently("http://localhost:8000/myfile")
    assert calls == ["http://localhost:8000/myfile"]


def test_open_browser_uses_powershell_when_available(monkeypatch):
    calls = []
    monkeypatch.setattr(server.shutil, "which", lambda name: "powershell.exe")
    monkeypatch.setattr(server.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    server.open_browser_silently("http://localhost:8000/myfile")
    assert calls
    assert calls[0][0][0][0] == "powershell.exe"


def test_start_server_reuses_existing_server(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(server, "SERVER_STATE", {"current_file": None, "is_running": True})
    opened = []
    monkeypatch.setattr(server, "open_browser_silently", lambda url: opened.append(url))
    monkeypatch.setattr(server, "cool_print", lambda text: None)

    server.start_server_and_open_browser(tmp_path / "art.txt")
    assert opened == ["http://localhost:8000/myfile"]
    assert server.SERVER_STATE["current_file"] == tmp_path / "art.txt"
