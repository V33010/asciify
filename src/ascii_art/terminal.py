# src/ascii_art/terminal.py
import sys
from pathlib import Path

from . import charset as charset_mod
from . import converter, image_loader, image_resize, ui


def run_terminal_mode(path_str, charset_arg, color_flag):
    """
    Handles the logic for the -t/--terminal workflow.
    """
    # 1. Validate Input
    p = Path(path_str)
    if not p.exists():
        print(f"Error: File '{path_str}' not found.")
        sys.exit(1)

    # 2. Load Image (No Previews)
    img = image_loader.load_image(p, preview=False)
    if not img:
        sys.exit(1)

    # 3. Auto-Calculate Sensible Dimensions
    target_w, target_h = image_resize.get_auto_terminal_dimensions(img)

    # 4. Resize
    img_resized = image_resize.resize_image(img, target_w, target_h)

    # 5. Get Charset
    try:
        chars = charset_mod.get_charset(charset_arg)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # 6. Convert & Print
    ui.soft_clear()

    if color_flag:
        # --- COLOR MODE ---
        ascii_grid = converter.image_to_ascii_with_color(img_resized, chars)

        for row in ascii_grid:
            line_parts = []
            for char, (r, g, b) in row:
                # Apply the "dot" styling but colored
                # display_str = char + "ˑ" if char != " " else char + " "
                # display_str = char + " "
                display_str = char + "."
                # display_str = char + char

                # Wrap in ANSI codes
                colored_str = ui.get_ansi_colored_string(display_str, r, g, b)
                line_parts.append(colored_str)

            sys.stdout.write("".join(line_parts) + "\n")

    else:
        # --- STANDARD B/W MODE ---
        ascii_grid = converter.image_to_ascii(img_resized, chars)

        for row in ascii_grid:
            # Apply the specific "dot" styling
            sys.stdout.write(
                "".join([char + "ˑ" if char != " " else char + " " for char in row])
                + "\n"
            )
