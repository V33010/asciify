# src/ascii_art/writer.py
import os
import re
from datetime import datetime
from pathlib import Path

from .ui import cool_print

OUTPUT_DIR = Path("assets/output")


def clean_filename(name):
    """
    Removes special characters, keeps only Alphanumeric English.
    """
    # Remove extension if user accidentally provided one via some logic,
    # though we handle that upstream usually.
    name_no_ext = os.path.splitext(name)[0]
    # Regex: keep a-z, A-Z, 0-9
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", name_no_ext)
    return cleaned


def save_art(ascii_grid, original_filename, custom_name=None):
    """
    Saves the ASCII grid to assets/output/
    Format: output_ddmmyyyy-HHMMSS_cleanName.txt
    """
    if not OUTPUT_DIR.exists():
        os.makedirs(OUTPUT_DIR)

    timestamp = datetime.now().strftime("%d%m%Y-%H%M%S")

    if custom_name:
        # User provided CLI output name
        base_name = clean_filename(custom_name)
    else:
        base_name = clean_filename(Path(original_filename).name)

    filename = f"output_{timestamp}_{base_name}.txt"
    filepath = OUTPUT_DIR / filename

    try:
        with open(filepath, "w") as f:
            for row in ascii_grid:
                # Join characters, add space for aspect ratio correction in terminal
                # Standard ASCII art usually puts a space to make square pixels look squareish
                f.write("".join([char + " " for char in row]))
                f.write("\n")

        cool_print(f"\nArt saved to file: {filepath}\n")
        return filepath
    except Exception as e:
        cool_print(f"Error saving file: {e}\n")
        return None
