from __future__ import annotations

import numpy as np
import pytest


def load_rust_module():
    return pytest.importorskip(
        "ascii_art.ascii_art_rs", reason="Rust extension not built"
    )


def test_image_to_ascii_rs_matches_python_grayscale_mapping_and_preserves_rgb():
    rust = load_rust_module()
    arr = np.array(
        [
            [[0, 0, 0], [10, 20, 30]],
            [[200, 50, 1], [255, 255, 255]],
        ],
        dtype=np.uint8,
    )
    chars = ["0", "1", "2", "3"]

    result = rust.image_to_ascii_rs(arr, chars)

    assert result[0][0] == ("0", (0, 0, 0))
    assert result[0][1] == ("0", (10, 20, 30))
    assert result[1][0] == ("2", (200, 50, 1))
    assert result[1][1] == ("3", (255, 255, 255))


def test_render_frame_to_string_produces_ansi_for_every_pixel():
    rust = load_rust_module()
    arr = np.array([[[1, 2, 3], [255, 0, 0]]], dtype=np.uint8)
    output = rust.render_frame_to_string(arr, ["0", "1"])

    assert output.count("\033[38;2;") == 2
    assert "\033[38;2;1;2;3m0.\033[0m" in output
    assert "\033[38;2;255;0;0m1.\033[0m" in output
    assert output.endswith("\n")


def test_grayscale_rust_renderer_matches_python_mapping_and_formatting():
    rust = load_rust_module()
    arr = np.array(
        [
            [[0, 0, 0], [10, 20, 30]],
            [[200, 50, 1], [255, 255, 255]],
        ],
        dtype=np.uint8,
    )

    output = rust.render_grayscale_to_string(arr, ["0", "1", "2", "3"])

    assert output == "0 0 \n2 3 \n"


def test_grayscale_rust_renderer_is_channel_order_invariant():
    rust = load_rust_module()
    bgr = np.array([[[10, 20, 30], [200, 50, 1]]], dtype=np.uint8)
    rgb = bgr[:, :, ::-1].copy()

    assert rust.render_grayscale_to_string(bgr, ["0", "1", "2", "3"]) == rust.render_grayscale_to_string(
        rgb, ["0", "1", "2", "3"]
    )


def test_grayscale_rust_renderer_rejects_empty_charset():
    rust = load_rust_module()
    arr = np.zeros((1, 1, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="non-empty"):
        rust.render_grayscale_to_string(arr, [])


def test_rust_frame_renderer_matches_color_grid_pixel_data():
    rust = load_rust_module()
    arr = np.array([[[0, 10, 20], [20, 10, 0]]], dtype=np.uint8)
    chars = [" ", "#", "@"]

    grid = rust.image_to_ascii_rs(arr, chars)
    rendered = rust.render_frame_to_string(arr, chars)

    assert grid[0][0][1] == (0, 10, 20)
    assert grid[0][1][1] == (20, 10, 0)
    assert rendered.count("\033[38;2;") == 2


def test_rust_renderers_preserve_output_for_non_contiguous_arrays():
    rust = load_rust_module()
    base = np.array(
        [
            [[1, 2, 3], [40, 50, 60], [70, 80, 90]],
            [[100, 110, 120], [130, 140, 150], [200, 210, 220]],
        ],
        dtype=np.uint8,
    )
    view = base[:, ::-1, :]
    chars = ["0", "1", "2", "3"]

    contiguous = np.ascontiguousarray(view)
    assert rust.render_grayscale_to_string(view, chars) == rust.render_grayscale_to_string(
        contiguous, chars
    )
    assert rust.render_frame_to_string(view, chars) == rust.render_frame_to_string(
        contiguous, chars
    )


def test_rust_charset_lut_matches_original_floor_mapping_for_all_u8_values():
    rust = load_rust_module()
    values = np.arange(256, dtype=np.uint8)
    arr = np.stack([values, values, values], axis=1).reshape(1, 256, 3)
    chars = list("abcdefghijklm")

    output = rust.render_grayscale_to_string(arr, chars)
    rendered_chars = output[:-1][::2]

    expected = "".join(
        chars[int(value) * (len(chars) - 1) // 255]
        for value in values
    )
    assert rendered_chars == expected


def test_rust_color_renderer_rejects_empty_charset():
    rust = load_rust_module()
    arr = np.zeros((1, 1, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="non-empty"):
        rust.render_frame_to_string(arr, [])
