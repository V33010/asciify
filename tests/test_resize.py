from __future__ import annotations

import os
import shutil

import numpy as np
import pytest
from PIL import Image

from ascii_art import image_resize


@pytest.fixture()
def img():
    return Image.new("RGB", (400, 200))


def test_calculate_dimensions_returns_both_targets_unchanged(img):
    assert image_resize.calculate_dimensions(img, 100, 60) == (100, 60)


def test_calculate_dimensions_calculates_height_from_width(img):
    assert image_resize.calculate_dimensions(img, target_w=100) == (100, 50)


def test_calculate_dimensions_calculates_width_from_height(img):
    assert image_resize.calculate_dimensions(img, target_h=75) == (150, 75)


def test_calculate_dimensions_honors_explicit_ratio_for_width(img):
    assert image_resize.calculate_dimensions(img, target_w=100, ratio=2.0) == (100, 50)


def test_calculate_dimensions_honors_explicit_ratio_for_height(img):
    assert image_resize.calculate_dimensions(img, target_h=50, ratio=2.5) == (125, 50)


def test_calculate_dimensions_rejects_conflicting_width_height_ratio(img):
    with pytest.raises(ValueError, match="Conflict"):
        image_resize.calculate_dimensions(img, 100, 100, ratio=2.0)


def test_calculate_dimensions_returns_none_pair_when_no_constraints(img):
    assert image_resize.calculate_dimensions(img) == (None, None)


def test_resize_image_changes_dimensions(img):
    resized = image_resize.resize_image(img, 37, 19)
    assert resized.size == (37, 19)


def test_resize_video_frame_uses_linear_interpolation(monkeypatch):
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    captured = {}
    sentinel = np.empty((56, 100, 3), dtype=np.uint8)

    def fake_resize(source, size, interpolation):
        captured["source"] = source
        captured["size"] = size
        captured["interpolation"] = interpolation
        return sentinel

    monkeypatch.setattr(image_resize.cv2, "resize", fake_resize)

    result = image_resize.resize_video_frame(frame, 100, 56)

    assert result is sentinel
    assert captured["source"] is frame
    assert captured["size"] == (100, 56)
    assert captured["interpolation"] == image_resize.cv2.INTER_LINEAR


def test_interactive_downsize_rejects_non_numeric_input_then_accepts(
    monkeypatch, capsys, img
):
    answers = iter(["abc", "2"])
    monkeypatch.setattr("builtins.input", lambda: next(answers))

    assert image_resize.interactive_downsize_factor(img) == (200, 100)
    assert "Invalid number" in capsys.readouterr().out


def test_interactive_downsize_rejects_factor_below_one_by_default(
    monkeypatch, capsys, img
):
    answers = iter(["0.5", "4"])
    monkeypatch.setattr("builtins.input", lambda: next(answers))

    assert image_resize.interactive_downsize_factor(img) == (100, 50)
    assert "must be >= 1" in capsys.readouterr().out


def test_interactive_downsize_allows_upscaling_when_bypassed(monkeypatch, img):
    monkeypatch.setattr("builtins.input", lambda: "0.5")
    assert image_resize.interactive_downsize_factor(img, bypass_downsizing=True) == (
        800,
        400,
    )


def test_interactive_downsize_rejects_nonpositive_factor_when_bypassed(
    monkeypatch, capsys, img
):
    answers = iter(["0", "-2", "4"])
    monkeypatch.setattr("builtins.input", lambda: next(answers))

    assert image_resize.interactive_downsize_factor(img, bypass_downsizing=True) == (
        100,
        50,
    )
    captured = capsys.readouterr().out
    assert "must be > 0" in captured


def test_interactive_downsize_rejects_resulting_zero_dimension(monkeypatch, capsys):
    tiny = Image.new("RGB", (3, 2))
    answers = iter(["10", "2"])
    monkeypatch.setattr("builtins.input", lambda: next(answers))

    assert image_resize.interactive_downsize_factor(tiny) == (1, 1)
    assert "too small" in capsys.readouterr().out


def test_auto_terminal_dimensions_fit_within_mocked_terminal(monkeypatch):
    monkeypatch.setattr(shutil, "get_terminal_size", lambda: os_terminal_size(80, 25))
    img = Image.new("RGB", (400, 200))

    width, height = image_resize.get_auto_terminal_dimensions(img)
    assert width >= 1 and height >= 1
    assert width * 2 + 2 <= 80
    assert height + 1 <= 25


def test_auto_terminal_dimensions_never_returns_zero(monkeypatch):
    monkeypatch.setattr(shutil, "get_terminal_size", lambda: os_terminal_size(4, 3))
    img = Image.new("RGB", (10, 10))

    width, height = image_resize.get_auto_terminal_dimensions(img)
    assert width >= 1 and height >= 1


def test_auto_terminal_dimensions_handles_wide_image(monkeypatch):
    monkeypatch.setattr(shutil, "get_terminal_size", lambda: os_terminal_size(120, 40))
    img = Image.new("RGB", (1600, 200))

    width, height = image_resize.get_auto_terminal_dimensions(img)
    assert width * 2 + 2 <= 120
    assert height + 1 <= 40


def os_terminal_size(columns: int, lines: int):
    return os.terminal_size((columns, lines))
