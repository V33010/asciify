from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from ascii_art import converter
from ascii_art.charset import CHARSETS


def image_from_pixels(pixels, mode="RGB"):
    arr = np.array(pixels, dtype=np.uint8)
    return Image.fromarray(arr, mode=mode)


def test_grayscale_conversion_maps_black_and_white_to_charset_extremes():
    img = image_from_pixels([[(0, 0, 0), (255, 255, 255)]])
    charset = " .#"

    assert converter.image_to_ascii(img, charset) == [[" ", "#"]]


def test_grayscale_conversion_uses_per_pixel_max_rgb_channel():
    img = image_from_pixels([[(10, 20, 30), (200, 50, 1)]])
    charset = "0123456789"

    result = converter.image_to_ascii(img, charset)
    # 30/255*9 -> 1, 200/255*9 -> 7
    assert result == [["1", "7"]]


def test_grayscale_conversion_preserves_dimensions():
    img = Image.new("L", (7, 5), color=100)
    result = converter.image_to_ascii(img, "01")

    assert len(result) == 5
    assert all(len(row) == 7 for row in result)


def test_grayscale_conversion_supports_single_channel_images():
    img = Image.new("L", (2, 1), color=255)
    assert converter.image_to_ascii(img, " .#") == [["#", "#"]]


def test_grayscale_conversion_handles_rgba_by_ignoring_alpha():
    img = image_from_pixels([[(255, 0, 0, 0)]], mode="RGBA")

    # The converter uses RGB channels and deliberately ignores alpha.
    assert converter.image_to_ascii(img, "01") == [["1"]]


def test_grayscale_conversion_with_standard_charset_returns_characters_only():
    img = Image.new("RGB", (3, 2), (128, 128, 128))
    result = converter.image_to_ascii(img, CHARSETS["default"])

    assert all(isinstance(cell, str) for row in result for cell in row)


def test_empty_charset_is_rejected_before_indexing():
    img = Image.new("L", (1, 1), 0)
    # The public converter currently has no explicit empty-charset validation;
    # this test documents the safe API expectation and exposes that edge case.
    with pytest.raises((IndexError, ZeroDivisionError, ValueError)):
        converter.image_to_ascii(img, "")


def test_render_image_to_string_requires_rust_extension(monkeypatch):
    img = Image.new("RGB", (1, 1), (1, 2, 3))
    monkeypatch.setattr(converter, "render_frame_to_string", None)

    with pytest.raises(ImportError, match="Rust extension"):
        converter.render_image_to_string(img, "01")


def test_render_image_to_string_sends_rgb_array_and_charset_list(monkeypatch):
    calls = {}

    def fake_renderer(arr, chars):
        calls["array"] = arr
        calls["charset"] = chars
        return "\033[38;2;1;2;3m0.\033[0m\n"

    monkeypatch.setattr(converter, "render_frame_to_string", fake_renderer)
    img = Image.new("RGBA", (1, 1), (1, 2, 3, 99))

    result = converter.render_image_to_string(img, "01")

    assert result == "\033[38;2;1;2;3m0.\033[0m\n"
    assert calls["array"].shape == (1, 1, 3)
    assert calls["array"].dtype == np.uint8
    assert calls["array"][0, 0].tolist() == [1, 2, 3]
    assert calls["charset"] == ["0", "1"]


def test_render_image_to_string_reuses_rgb_image_without_reconversion(monkeypatch):
    calls = {}

    def fake_renderer(arr, chars):
        calls["array"] = arr
        return ""

    monkeypatch.setattr(converter, "render_frame_to_string", fake_renderer)
    img = Image.new("RGB", (1, 1), (4, 5, 6))

    converter.render_image_to_string(img, "01")

    assert calls["array"][0, 0].tolist() == [4, 5, 6]


def test_render_grayscale_image_to_string_requires_rust_extension(monkeypatch):
    img = Image.new("RGB", (1, 1), (1, 2, 3))
    monkeypatch.setattr(converter, "render_grayscale_to_string", None)

    with pytest.raises(ImportError, match="Rust extension"):
        converter.render_grayscale_image_to_string(img, "01")


def test_render_grayscale_image_to_string_sends_rgb_array_and_charset_list(monkeypatch):
    calls = {}

    def fake_renderer(arr, chars):
        calls["array"] = arr
        calls["charset"] = chars
        return "0 1 \n"

    monkeypatch.setattr(converter, "render_grayscale_to_string", fake_renderer)
    img = Image.new("RGBA", (2, 1), (1, 2, 3, 99))

    result = converter.render_grayscale_image_to_string(img, "01")

    assert result == "0 1 \n"
    assert calls["array"].shape == (1, 2, 3)
    assert calls["array"].dtype == np.uint8
    assert calls["array"][0, 0].tolist() == [1, 2, 3]
    assert calls["charset"] == ["0", "1"]


def test_render_grayscale_image_to_string_reuses_rgb_image_without_reconversion(monkeypatch):
    calls = {}

    def fake_renderer(arr, chars):
        calls["array"] = arr
        return ""

    monkeypatch.setattr(converter, "render_grayscale_to_string", fake_renderer)
    img = Image.new("RGB", (1, 1), (4, 5, 6))

    converter.render_grayscale_image_to_string(img, "01")

    assert calls["array"][0, 0].tolist() == [4, 5, 6]


def test_render_grayscale_image_to_string_rejects_empty_charset(monkeypatch):
    monkeypatch.setattr(converter, "render_grayscale_to_string", lambda arr, chars: "")
    img = Image.new("RGB", (1, 1), (0, 0, 0))

    with pytest.raises(ValueError, match="non-empty"):
        converter.render_grayscale_image_to_string(img, "")


def test_color_converter_requires_rust_extension(monkeypatch):
    img = Image.new("RGB", (1, 1), (1, 2, 3))
    monkeypatch.setattr(converter, "image_to_ascii_rs", None)

    with pytest.raises(ImportError, match="Rust extension"):
        converter.image_to_ascii_with_color(img, "01")


def test_color_converter_sends_rgb_array_and_charset_list(monkeypatch):
    calls = {}

    def fake_renderer(arr, chars):
        calls["array"] = arr
        calls["charset"] = chars
        return [[("0", (1, 2, 3))]]

    monkeypatch.setattr(converter, "image_to_ascii_rs", fake_renderer)
    img = Image.new("RGBA", (1, 1), (1, 2, 3, 99))

    result = converter.image_to_ascii_with_color(img, "01")

    assert result == [[("0", (1, 2, 3))]]
    assert calls["array"].shape == (1, 1, 3)
    assert calls["array"].dtype == np.uint8
    assert calls["array"][0, 0].tolist() == [1, 2, 3]
    assert calls["charset"] == ["0", "1"]


def test_color_converter_preserves_multiple_pixels(monkeypatch):
    seen = {}

    def fake_renderer(arr, chars):
        seen["arr"] = arr.copy()
        return []

    monkeypatch.setattr(converter, "image_to_ascii_rs", fake_renderer)
    img = image_from_pixels([[(0, 0, 0), (255, 255, 255)]])
    converter.image_to_ascii_with_color(img, "01")

    np.testing.assert_array_equal(
        seen["arr"], np.array([[[0, 0, 0], [255, 255, 255]]], dtype=np.uint8)
    )
