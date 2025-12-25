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
    # Handle --show-charsets
    if hasattr(args, "show_charsets") and args.show_charsets:
        print(f"\nAvailable Charsets:")
        for name, chars in charset_mod.CHARSETS.items():
            print(f"  • {name:<15} : {chars}")
        print()
        # If input file is NOT provided, we exit here.
        # If it IS provided, we continue to process the image.
        if not args.input_file:
            return

    # Handle --set-charset
    if hasattr(args, "set_charset") and args.set_charset:
        try:
            charset_mod.set_persistent_charset(args.set_charset)
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
        # If no input, exit
        if not args.input_file:
            return

    # --- 2. INPUT VALIDATION ---
    if not args.input_file:
        print("Error: Input file is required. Use -i/--input-file <path>")
        sys.exit(1)

    p = Path(args.input_file)
    if not p.exists():
        print(f"Error: Input file '{args.input_file}' not found.")
        sys.exit(1)

    # --- 3. LOAD IMAGE ---
    img = image_loader.load_image(p, preview=False)
    if not img:
        sys.exit(1)

    # --- 4. CALCULATE DIMENSIONS ---
    # Check for conflict: 3 flags provided but ratio doesn't match
    if args.width and args.height and args.aspect_ratio:
        calc_ratio = args.width / args.height
        if abs(calc_ratio - args.aspect_ratio) > 0.01:
            print(
                f"❌ Error: Provided width ({args.width}) and height ({args.height}) implies ratio {calc_ratio:.2f}, but --aspect-ratio was {args.aspect_ratio}."
            )
            sys.exit(1)

    target_w, target_h = None, None

    # Case A: User provided specific dimensions
    if args.width or args.height:
        try:
            target_w, target_h = image_resize.calculate_dimensions(
                img, args.width, args.height, args.aspect_ratio
            )
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    # Case B: User provided downsize factor
    elif args.downsize:
        # Custom logic for simple downsize factor
        try:
            factor = float(args.downsize)
            if factor <= 0:
                raise ValueError
            target_w = int(img.width / factor)
            target_h = int(img.height / factor)
        except ValueError:
            print("Error: --downsize must be a positive number.")
            sys.exit(1)

    # Case C: Default (Auto-fit to terminal)
    else:
        target_w, target_h = image_resize.get_auto_terminal_dimensions(img)

    # --- 5. RESIZE ---
    img_resized = image_resize.resize_image(img, target_w, target_h)

    # --- 6. DETERMINE CHARSET ---
    # args.charset is the custom flag (-c). get_charset handles the priority logic.
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
    # We always print unless user explicitly suppressed it?
    # Prompt says: "printing output in the terminal will be the default thing happening."
    # If saving is requested, we usually still print, unless the output is huge, but prompt implies printing AND saving is possible.

    # Render string for terminal
    for row in ascii_grid:
        line_parts = []
        for item in row:
            if isinstance(item, tuple):
                char, (r, g, b) = item
                display_str = char + "."  # specific dot styling
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
            original_filename=p,
            output_folder=args.output_folder,
            output_name=args.output_file_name,
            as_html=args.html,
        )
