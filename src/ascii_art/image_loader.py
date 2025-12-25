# src/ascii_art/image_loader.py
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from . import url_image_loader  # Import new handler
from .ui import clear_terminal, cool_print

# --- SMART PATHING LOGIC ---
REPO_INPUT = Path("assets/input")
if REPO_INPUT.exists() and REPO_INPUT.is_dir():
    INPUT_DIR = REPO_INPUT
    MODE = "REPO"
else:
    INPUT_DIR = Path(".")
    MODE = "USER"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}


def list_and_select_image():
    files = []
    for filepath in INPUT_DIR.iterdir():
        if filepath.is_file():
            if filepath.suffix.lower() in IMAGE_EXTENSIONS:
                files.append(filepath)

    if not files:
        if MODE == "REPO":
            cool_print(f"No files found in {INPUT_DIR}\n")
        else:
            cool_print("No image files found in the current directory.\n")
            cool_print("Tip: Run this command inside a folder containing images.\n")
        return None

    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    cool_print(f"Scanning: {INPUT_DIR.resolve()}\n")
    cool_print("Available images (sorted by newest):\n")

    max_show = 15
    for idx, f in enumerate(files[:max_show]):
        print(f"[{idx}] {f.name}")

    if len(files) > max_show:
        print(f"... and {len(files) - max_show} more.")

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


def _smart_preview(path):
    path_str = str(path)
    if shutil.which("powershell.exe"):
        try:
            subprocess.run(
                ["powershell.exe", "-c", "start", f"'{path_str}'"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            pass

    has_display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    if not has_display:
        return False

    try:
        img = Image.open(path)
        img.show()
        return True
    except Exception:
        return False


def load_image(source, preview=True):
    """
    Loads an image from a Path object OR a URL string.
    """
    # 1. URL HANDLING
    if isinstance(source, str) and source.startswith(("http://", "https://")):
        # URLs are never previewed (we don't save to disk)
        data, filename = url_image_loader.download_image(source)
        if not data:
            return None

        try:
            img = Image.open(data)
            # Attach the original filename to the object metadata
            # This allows terminal.py to use it for saving without a real file path
            img.info["custom_filename"] = filename
            return img
        except Exception as e:
            cool_print(f"Error opening downloaded image data: {e}\n")
            return None

    # 2. LOCAL FILE HANDLING
    try:
        img = Image.open(source)
        if preview:
            cool_print(f"Opening {source} for preview...\n")
            success = _smart_preview(source)
            if not success:
                cool_print("Warning: No suitable display found. Skipping preview.\n")
        return img
    except Exception as e:
        cool_print(f"Error loading image: {e}\n")
        return None
