# src/ascii_art/writer.py
import os
import re
from datetime import datetime
from pathlib import Path

from .ui import cool_print

# --- SMART PATHING LOGIC ---
REPO_OUTPUT = Path("assets/output")

if REPO_OUTPUT.exists() and REPO_OUTPUT.is_dir():
    # Dev Mode: Keep output organized in assets/output
    OUTPUT_DIR = REPO_OUTPUT
else:
    # User Mode: Save to current directory
    OUTPUT_DIR = Path(".")


def clean_filename(name):
    name_no_ext = os.path.splitext(name)[0]
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", name_no_ext)
    return cleaned


def save_art(ascii_grid, original_filename, custom_name=None):
    # Ensure directory exists (mostly for REPO mode or if user deleted it)
    if not OUTPUT_DIR.exists():
        try:
            os.makedirs(OUTPUT_DIR)
        except OSError:
            # Fallback to current dir if permission denied
            pass

    timestamp = datetime.now().strftime("%d%m%Y-%H%M%S")

    if custom_name:
        base_name = clean_filename(custom_name)
        # If user gave a custom name, use it exactly
        filename = f"{base_name}.txt"
    else:
        # Auto-generated name
        base_name = clean_filename(Path(original_filename).name)
        # Prefix with 'ascii_' so we don't get lost in user folders
        filename = f"ascii_{base_name}_{timestamp}.txt"

    filepath = OUTPUT_DIR / filename

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            for row in ascii_grid:
                # Handle both standard list output and tuple (color) output logic
                # For file saving, we strip color info if it exists
                clean_row = []
                for item in row:
                    if isinstance(item, tuple):
                        # item is (char, rgb)
                        char = item[0]
                    else:
                        # item is char
                        char = item

                    # Add space for aspect ratio
                    clean_row.append(char + " ")

                f.write("".join(clean_row))
                f.write("\n")

        cool_print(f"\nArt saved to file: {filepath}\n")
        return filepath
    except Exception as e:
        cool_print(f"Error saving file: {e}\n")
        return None
