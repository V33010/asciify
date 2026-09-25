from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from PIL import Image

from ascii_art import image_loader


def make_image(path: Path, size=(4, 3), color=(10, 20, 30)):
    Image.new("RGB", size, color).save(path)


def test_load_image_reads_local_file_without_preview(tmp_path):
    path = tmp_path / "input.png"
    make_image(path)

    img = image_loader.load_image(path, preview=False)
    assert img is not None
    assert img.size == (4, 3)
    assert img.mode == "RGB"


def test_load_image_returns_none_for_missing_or_invalid_file(tmp_path, capsys):
    img = image_loader.load_image(tmp_path / "missing.png", preview=False)
    assert img is None
    assert "Error loading image" in capsys.readouterr().out


def test_load_image_local_preview_invokes_smart_preview(monkeypatch, tmp_path):
    path = tmp_path / "input.png"
    make_image(path)
    called = []
    monkeypatch.setattr(image_loader, "_smart_preview", lambda p: called.append(p) or True)

    img = image_loader.load_image(path, preview=True)
    assert img is not None
    assert called == [path]


def test_load_image_url_path_attaches_downloaded_filename(monkeypatch):
    from io import BytesIO

    payload = BytesIO()
    Image.new("RGB", (2, 2), (1, 2, 3)).save(payload, format="PNG")
    payload.seek(0)

    monkeypatch.setattr(
        image_loader.url_image_loader,
        "download_image",
        lambda url: (payload, "remote image.png"),
    )

    img = image_loader.load_image("https://example.com/image.png", preview=True)
    assert img is not None
    assert img.info["custom_filename"] == "remote image.png"
    assert img.size == (2, 2)


def test_load_image_url_download_failure_returns_none(monkeypatch):
    monkeypatch.setattr(
        image_loader.url_image_loader,
        "download_image",
        lambda url: (None, None),
    )
    assert image_loader.load_image("https://example.com/missing.png", preview=False) is None


def test_list_and_select_image_sorts_newest_first(monkeypatch, tmp_path):
    older = tmp_path / "older.png"
    newer = tmp_path / "newer.jpg"
    not_image = tmp_path / "notes.txt"
    make_image(older)
    make_image(newer)
    not_image.write_text("x", encoding="utf-8")

    now = time.time()
    os.utime(older, (now - 100, now - 100))
    os.utime(newer, (now, now))
    monkeypatch.setattr(image_loader, "INPUT_DIR", tmp_path)
    monkeypatch.setattr(image_loader, "MODE", "USER")
    monkeypatch.setattr("builtins.input", lambda: "0")

    selected = image_loader.list_and_select_image()
    assert selected == newer


def test_list_and_select_image_retries_bad_input(monkeypatch, tmp_path, capsys):
    image = tmp_path / "image.png"
    make_image(image)
    monkeypatch.setattr(image_loader, "INPUT_DIR", tmp_path)
    monkeypatch.setattr(image_loader, "MODE", "USER")
    answers = iter(["not-a-number", "99", "0"])
    monkeypatch.setattr("builtins.input", lambda: next(answers))

    assert image_loader.list_and_select_image() == image
    output = capsys.readouterr().out
    assert "valid number" in output
    assert "Invalid index" in output


def test_list_and_select_image_returns_none_when_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(image_loader, "INPUT_DIR", tmp_path)
    monkeypatch.setattr(image_loader, "MODE", "USER")
    assert image_loader.list_and_select_image() is None


def test_smart_preview_returns_false_without_display(monkeypatch, tmp_path):
    path = tmp_path / "input.png"
    make_image(path)
    monkeypatch.setattr(image_loader.shutil, "which", lambda name: None)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    assert image_loader._smart_preview(path) is False


def test_smart_preview_uses_powershell_when_available(monkeypatch, tmp_path):
    path = tmp_path / "input.png"
    make_image(path)
    calls = []

    monkeypatch.setattr(image_loader.shutil, "which", lambda name: "powershell.exe")
    monkeypatch.setattr(
        image_loader.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert image_loader._smart_preview(path) is True
    assert calls
    assert calls[0][0][0][0] == "powershell.exe"
