from __future__ import annotations

from io import BytesIO

import pytest

from ascii_art import url_image_loader


class FakeResponse:
    def __init__(self, data=b"image-data", headers=None, chunks=None):
        self.data = data
        self.headers = headers or {}
        self.chunks = chunks
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getheader(self, name):
        return self.headers.get(name)

    def read(self, chunk_size=-1):
        if self.chunks is not None:
            if not self.chunks:
                return b""
            return self.chunks.pop(0)
        if chunk_size < 0:
            return self.data
        chunk = self.data[self.offset : self.offset + chunk_size]
        self.offset += len(chunk)
        return chunk


def test_supported_http_url_downloads_and_extracts_filename(monkeypatch):
    fake = FakeResponse(
        b"abc",
        headers={"Content-Length": "3", "Content-Type": "image/png"},
    )
    calls = []
    monkeypatch.setattr(
        url_image_loader.urllib.request,
        "urlopen",
        lambda req, timeout: calls.append((req, timeout)) or fake,
    )

    data, filename = url_image_loader.download_image("https://example.com/path/pic.png")

    assert data is not None
    assert data.read() == b"abc"
    assert filename == "pic.png"
    assert calls[0][1] == url_image_loader.TIMEOUT_SECONDS
    assert calls[0][0].headers["User-agent"] == url_image_loader.USER_AGENT


def test_url_query_string_does_not_enter_filename():
    fake = FakeResponse(
        b"abc",
        headers={"Content-Type": "image/jpeg", "Content-Length": "3"},
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        url_image_loader.urllib.request, "urlopen", lambda *args, **kwargs: fake
    )
    try:
        _, filename = url_image_loader.download_image("https://example.com/foo.jpg?x=1")
    finally:
        monkeypatch.undo()
    assert filename == "foo.jpg"


def test_malformed_or_disallowed_scheme_is_rejected(capsys):
    assert url_image_loader.download_image("ftp://example.com/a.png") == (None, None)
    assert "must start" in capsys.readouterr().out


def test_invalid_content_type_is_rejected(monkeypatch, capsys):
    fake = FakeResponse(headers={"Content-Type": "text/plain", "Content-Length": "10"})
    monkeypatch.setattr(
        url_image_loader.urllib.request, "urlopen", lambda *args, **kwargs: fake
    )

    assert url_image_loader.download_image("https://example.com/a.txt") == (None, None)
    assert "Invalid Content-Type" in capsys.readouterr().out


def test_parameterized_content_type_is_accepted(monkeypatch):
    fake = FakeResponse(
        b"abc",
        headers={"Content-Type": "image/png; charset=utf-8", "Content-Length": "3"},
    )
    monkeypatch.setattr(
        url_image_loader.urllib.request, "urlopen", lambda *args, **kwargs: fake
    )
    data, filename = url_image_loader.download_image("https://example.com/a.png")
    assert data is not None
    assert filename == "a.png"


def test_content_length_over_limit_is_rejected(monkeypatch, capsys):
    fake = FakeResponse(
        headers={
            "Content-Length": str(url_image_loader.MAX_DOWNLOAD_SIZE + 1),
            "Content-Type": "image/png",
        }
    )
    monkeypatch.setattr(
        url_image_loader.urllib.request, "urlopen", lambda *args, **kwargs: fake
    )

    assert url_image_loader.download_image("https://example.com/a.png") == (None, None)
    assert "too large" in capsys.readouterr().out


def test_streamed_download_over_limit_is_rejected(monkeypatch, capsys):
    too_much = url_image_loader.MAX_DOWNLOAD_SIZE + 1
    fake = FakeResponse(
        headers={"Content-Type": "image/png"},
        chunks=[b"x" * too_much, b""],
    )
    monkeypatch.setattr(
        url_image_loader.urllib.request, "urlopen", lambda *args, **kwargs: fake
    )

    assert url_image_loader.download_image("https://example.com/a.png") == (None, None)
    assert "exceeded maximum size" in capsys.readouterr().out


def test_missing_extension_uses_mime_based_fallback(monkeypatch):
    fake = FakeResponse(
        b"abc",
        headers={"Content-Type": "image/png", "Content-Length": "3"},
    )
    monkeypatch.setattr(
        url_image_loader.urllib.request, "urlopen", lambda *args, **kwargs: fake
    )

    _, filename = url_image_loader.download_image("https://example.com/no-extension")
    assert filename == "downloaded_image.png"


def test_missing_extension_with_parameterized_png_content_type_uses_safe_default(
    monkeypatch,
):
    fake = FakeResponse(
        b"abc",
        headers={"Content-Type": "image/png; charset=utf-8", "Content-Length": "3"},
    )
    monkeypatch.setattr(
        url_image_loader.urllib.request, "urlopen", lambda *args, **kwargs: fake
    )

    _, filename = url_image_loader.download_image("https://example.com/no-extension")
    # Documents the current implementation's exact fallback behavior.
    assert filename == "downloaded_image.png"


def test_http_error_returns_none(monkeypatch, capsys):
    class FakeHTTPError(Exception):
        code = 404
        reason = "Not Found"

    # urllib.error.HTTPError is a concrete exception and can be raised directly.
    err = __import__("urllib.error", fromlist=["HTTPError"]).HTTPError(
        "https://example.com/a.png", 404, "Not Found", {}, None
    )
    monkeypatch.setattr(
        url_image_loader.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(err),
    )

    assert url_image_loader.download_image("https://example.com/a.png") == (None, None)
    assert "HTTP Error: 404" in capsys.readouterr().out


def test_url_error_returns_none(monkeypatch, capsys):
    err = __import__("urllib.error", fromlist=["URLError"]).URLError("offline")
    monkeypatch.setattr(
        url_image_loader.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(err),
    )

    assert url_image_loader.download_image("https://example.com/a.png") == (None, None)
    assert "Network Error" in capsys.readouterr().out


def test_missing_extension_parameterized_png_should_use_png_extension(monkeypatch):
    fake = FakeResponse(
        b"abc",
        headers={"Content-Type": "image/png; charset=utf-8", "Content-Length": "3"},
    )
    monkeypatch.setattr(
        url_image_loader.urllib.request, "urlopen", lambda *args, **kwargs: fake
    )

    _, filename = url_image_loader.download_image("https://example.com/no-extension")
    assert filename == "downloaded_image.png"
