# src/ascii_art/image_loader.py
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from .ui import clear_terminal, cool_print

# --- SMART PATHING LOGIC ---
# If running inside the dev repo, use assets/input.
# If installed via pip (user mode), use the current working directory.
REPO_INPUT = Path("assets/input")
if REPO_INPUT.exists() and REPO_INPUT.is_dir():
    INPUT_DIR = REPO_INPUT
    MODE = "REPO"
else:
    INPUT_DIR = Path(".")
    MODE = "USER"

# Supported extensions to filter noise in User Mode
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}


def list_and_select_image():
    # In User Mode, we don't error if dir is missing (it's always '.')
    # But we might error if no images are found.

    files = []
    # Use glob to find files, but filter by extension
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

    # Sort by modification time (descending)
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    cool_print(f"Scanning: {INPUT_DIR.resolve()}\n")
    cool_print("Available images (sorted by newest):\n")

    # Limit list to top 15 to avoid cluttering terminal in large folders
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


def load_image(path, preview=True):
    try:
        img = Image.open(path)
        if preview:
            cool_print(f"Opening {path} for preview...\n")
            success = _smart_preview(path)
            if not success:
                cool_print("Warning: No suitable display found. Skipping preview.\n")
        return img
    except Exception as e:
        cool_print(f"Error loading image: {e}\n")
        return None
