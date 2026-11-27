# src/ascii_art/writer.py
import html
import os
import re
from datetime import datetime
from pathlib import Path

import numpy as np


def clean_filename(name):
    """Sanitizes a string to be safe for filenames."""
    # Allow alphanumeric, underscores, and hyphens.
    name_no_ext = os.path.splitext(name)[0]
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "", name_no_ext)
    return cleaned


def generate_html(ascii_grid):
    """Generates an HTML string from the ASCII grid."""
    lines = []
    lines.append("<!DOCTYPE html>")
    lines.append('<html><head><meta charset="utf-8"><style>')
    lines.append(
        "body { background-color: #000; color: #fff; font-family: monospace; white-space: pre; line-height: 1.0; }"
    )
    lines.append("</style></head><body>")

    for row in ascii_grid:
        line_html = ""
        for item in row:
            if isinstance(item, tuple):
                char, (r, g, b) = item
                # Escape the char for HTML (<, >, &)
                safe_char = html.escape(char)
                line_html += f'<span style="color: rgb({r},{g},{b})">{safe_char}</span>'
            else:
                safe_char = html.escape(item)
                line_html += safe_char
        lines.append(line_html)

    lines.append("</body></html>")
    return "\n".join(lines)


def generate_fill_html(rgb_array, hd=False):
    """Generates a zero-whitespace full-fill HTML document from an RGB image array."""
    arr = np.asarray(rgb_array)
    rows, cols = arr.shape[:2]

    lines = [
        "<!DOCTYPE html>",
        '<html><head><meta charset="utf-8"><style>',
        "body { background-color: #000; color: #fff; font-family: monospace; white-space: pre; line-height: 1.0; margin: 0; }",
        "</style></head><body>",
    ]

    if not hd:
        for r in range(rows):
            parts = []
            c = 0
            while c < cols:
                rv, gv, bv = int(arr[r, c, 0]), int(arr[r, c, 1]), int(arr[r, c, 2])
                run = 1
                while (
                    c + run < cols
                    and int(arr[r, c + run, 0]) == rv
                    and int(arr[r, c + run, 1]) == gv
                    and int(arr[r, c + run, 2]) == bv
                ):
                    run += 1
                parts.append(
                    f'<span style="background-color: rgb({rv},{gv},{bv})">{"  " * run}</span>'
                )
                c += run
            lines.append("".join(parts))
    else:
        for r in range(0, rows, 2):
            bot_r = r + 1 if r + 1 < rows else r
            parts = []
            c = 0
            while c < cols:
                top = (int(arr[r, c, 0]), int(arr[r, c, 1]), int(arr[r, c, 2]))
                bot = (
                    int(arr[bot_r, c, 0]),
                    int(arr[bot_r, c, 1]),
                    int(arr[bot_r, c, 2]),
                )
                run = 1
                while c + run < cols:
                    ntop = (
                        int(arr[r, c + run, 0]),
                        int(arr[r, c + run, 1]),
                        int(arr[r, c + run, 2]),
                    )
                    nbot = (
                        int(arr[bot_r, c + run, 0]),
                        int(arr[bot_r, c + run, 1]),
                        int(arr[bot_r, c + run, 2]),
                    )
                    if ntop == top and nbot == bot:
                        run += 1
                    else:
                        break
                if top == bot:
                    parts.append(
                        f'<span style="background-color: rgb({top[0]},{top[1]},{top[2]})">{" " * run}</span>'
                    )
                else:
                    parts.append(
                        f'<span style="color: rgb({top[0]},{top[1]},{top[2]}); background-color: rgb({bot[0]},{bot[1]},{bot[2]})">{"▀" * run}</span>'
                    )
                c += run
            lines.append("".join(parts))

    lines.append("</body></html>")
    return "\n".join(lines)


def save_art(
    ascii_grid,
    original_filename,
    output_folder=None,
    output_name=None,
    as_html=False,
    fill_mode=None,
):
    """
    Saves the ASCII art to a file.

    Args:
        ascii_grid: The 2D list of chars or (char, rgb) tuples, or an RGB image/array when fill_mode is set.
        original_filename: Path to the input image (used for auto-naming).
        output_folder: Directory to save in (defaults to CWD).
        output_name: Specific filename (WITHOUT extension).
        as_html: Boolean to save as .html instead of .txt.
        fill_mode: Optional "fill" or "fill_hd" for full-fill HTML output.
    """

    # 1. Determine Output Directory
    if output_folder:
        target_dir = Path(output_folder)
        if not target_dir.exists():
            # "make the location first" as requested
            try:
                os.makedirs(target_dir, exist_ok=True)
            except OSError as e:
                print(f"❌ Error creating directory '{output_folder}': {e}")
                return None
    else:
        target_dir = Path.cwd()

    # 2. Determine File Name
    timestamp = datetime.now().strftime("%d%m%Y-%H%M%S")
    extension = ".html" if as_html else ".txt"

    if output_name:
        # Check for user-provided extension
        _, ext = os.path.splitext(output_name)
        if ext:
            print(
                f"❌ Error: Output file name '{output_name}' must NOT include an extension."
            )
            return None

        # Use exact name provided by user
        final_filename = f"{output_name}{extension}"
    else:
        # Auto-generate name based on input file
        base_name = clean_filename(Path(original_filename).name) or "image"
        final_filename = f"ascii_{base_name}_{timestamp}{extension}"

    filepath = target_dir / final_filename

    # 3. Write File
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            if as_html:
                if fill_mode in ("fill", "fill_hd"):
                    html_content = generate_fill_html(
                        ascii_grid, hd=(fill_mode == "fill_hd")
                    )
                else:
                    html_content = generate_html(ascii_grid)
                f.write(html_content)
            else:
                for row in ascii_grid:
                    clean_row = []
                    for item in row:
                        if isinstance(item, tuple):
                            char = item[0]
                        else:
                            char = item
                        # Add space for aspect ratio correction in text files
                        clean_row.append(char + " ")
                    f.write("".join(clean_row) + "\n")

        print(f"✅ Output saved to: {filepath}")
        return filepath

    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return None
