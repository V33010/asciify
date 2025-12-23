# src/ascii_art/image_loader.py
import glob
import os
from pathlib import Path

from PIL import Image

from .ui import cool_print

# Define paths relative to the project root
INPUT_DIR = Path("assets/input")


def list_and_select_image():
    if not INPUT_DIR.exists():
        cool_print(f"Error: Directory {INPUT_DIR} does not exist.\n")
        return None

    files = []
    for filepath in INPUT_DIR.iterdir():
        if filepath.is_file() and filepath.name != ".gitkeep":
            files.append(filepath)

    if not files:
        cool_print("No files found in assets/input/\n")
        return None

    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    cool_print("Available images (sorted by newest):\n")
    for idx, f in enumerate(files):
        print(f"[{idx}] {f.name}")
    print()

    while True:
        cool_print("Enter the index of the image file: ")
        try:
            selection = input().strip()
            idx = int(selection)
            if 0 <= idx < len(files):
                return files[idx]
            else:
                cool_print("Invalid index. Try again.\n")
        except ValueError:
            cool_print("Please enter a valid number.\n")


def load_image(path, preview=True):
    try:
        img = Image.open(path)
        if preview:
            cool_print(f"Opening {path} for preview...\n")
            try:
                img.show()
            except Exception:
                cool_print(
                    "Warning: Could not open image preview (WSL/Display issue).\n"
                )
        return img
    except Exception as e:
        cool_print(f"Error loading image: {e}\n")
        return None
