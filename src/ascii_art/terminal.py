# src/ascii_art/terminal.py
import shutil
import sys
from pathlib import Path

from . import charset as charset_mod
from . import converter, image_loader, image_resize, ui, writer


def run_terminal_pipeline(args):
    """
    Main logic for the terminal-first workflow.
    args: The Namespace object from argparse.
    """

    # --- 1. CHARSET OPERATIONS ---
    if hasattr(args, "show_charsets") and args.show_charsets:
        print(f"\nAvailable Charsets:")
        for name, chars in charset_mod.CHARSETS.items():
            print(f"  • {name:<15} : {chars}")
        print()
        if not args.input_file:
            return

    if hasattr(args, "set_charset") and args.set_charset:
        try:
            charset_mod.set_persistent_charset(args.set_charset)
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
        if not args.input_file:
            return

    # --- 2. INPUT VALIDATION & 3. LOAD IMAGE ---
    if not args.input_file:
        print("Error: Input file is required. Use -i/--input-file <path>")
        sys.exit(1)

    # Check if input is URL or Local File
    is_url = args.input_file.startswith(("http://", "https://"))

    img = None
    original_path_obj = None

    if is_url:
        # Load directly (image_loader handles download)
        img = image_loader.load_image(args.input_file, preview=False)
        if not img:
            sys.exit(1)

        # Recover the filename we extracted during download
        # Default to a safe fallback if missing
        fname = img.info.get("custom_filename", "downloaded_image.jpg")

        original_path_obj = Path(fname)

    else:
        # Standard Local File Check
        p = Path(args.input_file)
        if not p.exists():
            print(f"Error: Input file '{args.input_file}' not found.")
            sys.exit(1)

        original_path_obj = p
        img = image_loader.load_image(p, preview=False)
        if not img:
            sys.exit(1)

    # --- 4. CALCULATE DIMENSIONS ---
    if args.width and args.height and args.aspect_ratio:
        calc_ratio = args.width / args.height
        if abs(calc_ratio - args.aspect_ratio) > 0.01:
            print(
                f"❌ Error: Provided width ({args.width}) and height ({args.height}) implies ratio {calc_ratio:.2f}, but --aspect-ratio was {args.aspect_ratio}."
            )
            sys.exit(1)

    target_w, target_h = None, None

    if args.width or args.height:
        try:
            target_w, target_h = image_resize.calculate_dimensions(
                img, args.width, args.height, args.aspect_ratio
            )
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif args.downsize:
        try:
            factor = float(args.downsize)
            if factor <= 0:
                raise ValueError
            target_w = int(img.width / factor)
            target_h = int(img.height / factor)
        except ValueError:
            print("Error: --downsize must be a positive number.")
            sys.exit(1)

    else:
        target_w, target_h = image_resize.get_auto_terminal_dimensions(img)

    # --- 5. RESIZE ---
    img_resized = image_resize.resize_image(img, target_w, target_h)

    # --- 6. DETERMINE CHARSET ---
    try:
        chars = charset_mod.get_charset(args.charset)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # --- 7. CONVERSION ---
    if args.color:
        ascii_grid = converter.image_to_ascii_with_color(img_resized, chars)
    else:
        ascii_grid = converter.image_to_ascii(img_resized, chars)

    # --- 8. OUTPUT TO TERMINAL ---
    for row in ascii_grid:
        line_parts = []
        for item in row:
            if isinstance(item, tuple):
                char, (r, g, b) = item
                display_str = char + "."
                colored_str = ui.get_ansi_colored_string(display_str, r, g, b)
                line_parts.append(colored_str)
            else:
                char = item
                line_parts.append(char + " ")

        sys.stdout.write("".join(line_parts) + "\n")

    # --- 9. SAVE TO FILE (Optional) ---
    should_save = any([args.save, args.output_folder, args.output_file_name, args.html])

    if should_save:
        writer.save_art(
            ascii_grid,
            original_filename=original_path_obj,
            output_folder=args.output_folder,
            output_name=args.output_file_name,
            as_html=args.html,
        )
