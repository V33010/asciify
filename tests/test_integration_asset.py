from __future__ import annotations

from pathlib import Path

import pytest

from ascii_art import converter, image_loader, image_resize
from ascii_art.charset import CHARSETS


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "assets" / "input"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}


def find_repo_image() -> Path | None:
    preferred = [INPUT / "sample-image.png", INPUT / "sample-image.jpg", INPUT / "sample.png", INPUT / "sample.jpg"]
    for path in preferred:
        if path.is_file():
            return path
    if not INPUT.exists():
        return None
    return next((p for p in sorted(INPUT.iterdir()) if p.suffix.lower() in IMAGE_EXTENSIONS), None)


def test_shipped_sample_image_loads_and_converts_end_to_end():
    path = find_repo_image()
    if path is None:
        pytest.skip("No sample image is present in assets/input in this checkout")

    img = image_loader.load_image(path, preview=False)
    assert img is not None
    target_w, target_h = image_resize.calculate_dimensions(img, target_w=min(img.width, 32))
    resized = image_resize.resize_image(img, target_w, target_h)
    grid = converter.image_to_ascii(resized, CHARSETS["default"])

    assert len(grid) == target_h
    assert all(len(row) == target_w for row in grid)
