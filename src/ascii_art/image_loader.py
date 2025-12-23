# src/ascii_art/image_loader.py
import glob
import os
from pathlib import Path

from PIL import Image

from .ui import cool_print

# Define paths relative to the project root assuming running from root
INPUT_DIR = Path("assets/input")


def list_and_select_image():
    """
    Lists files in assets/input sorted by date (descending).
    Asks user to select one by index.
    """
    # Ensure directory exists
    if not INPUT_DIR.exists():
        cool_print(f"Error: Directory {INPUT_DIR} does not exist.\n")
        return None

    # Get all files
    files = []
    for filepath in INPUT_DIR.iterdir():
        if filepath.is_file() and filepath.name != ".gitkeep":
            files.append(filepath)

    if not files:
        cool_print("No files found in assets/input/\n")
        return None

    # Sort by modification time (descending)
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
    """
    Loads an image from a path and optionally shows it.
    """
    try:
        img = Image.open(path)
        if preview:
            cool_print(f"Opening {path} for preview...\n")
            img.show()
            # No interactive confirmation here to keep CLI flow smooth,
            # checks happen in main flow if needed.
        return img
    except Exception as e:
        cool_print(f"Error loading image: {e}\n")
        return None
