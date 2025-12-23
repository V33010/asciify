# src/ascii_art/image_loader.py
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from .ui import clear_terminal, cool_print

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


def _smart_preview(path):
    """
    Attempts to open the image using the best available method
    without causing error dump noise.
    """
    path_str = str(path)

    # 1. WSL Strategy: Try using Windows native 'start' via PowerShell
    # This is fast, silent, and uses the default Windows Photo Viewer.
    if shutil.which("powershell.exe"):
        try:
            # We redirect stderr to DEVNULL to silence any 'interop' warnings
            subprocess.run(
                ["powershell.exe", "-c", "start", f"'{path_str}'"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            pass

    # 2. Linux Strategy: Check if a GUI (X11/Wayland) is actually available.
    # If variables are missing, img.show() will fail/crash, so we skip it.
    has_display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    if not has_display:
        return False

    # 3. Fallback: Standard PIL show
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
            else:
                # If we successfully opened it, we might want a tiny cleanup
                # but no massive delays or clear_terminal is needed anymore
                # because we silenced the stderr in the subprocess call.
                pass

        return img
    except Exception as e:
        cool_print(f"Error loading image: {e}\n")
        return None
