# src/ascii_art/cli.py
import argparse
import os
import sys
from pathlib import Path

from . import charset as charset_mod
from . import converter, image_loader, image_resize, server, ui, writer


def parse_args():
    parser = argparse.ArgumentParser(description="Convert images to ASCII art")

    parser.add_argument("-i", "--input", help="Path to input image")
    parser.add_argument("-o", "--output", help="Output filename (no extension)")
    parser.add_argument("-c", "--charset", help="Custom charset string")
    parser.add_argument("--no-preview", action="store_true", help="Skip image preview")
    parser.add_argument(
        "--no-animate", action="store_true", help="Disable text animation"
    )
    parser.add_argument("-w", "--width", type=int, help="Target width")
    parser.add_argument("-h", "--height", type=int, help="Target height")
    parser.add_argument("--ratio", type=float, help="Target aspect ratio")

    return parser.parse_args()


def process_workflow(args):
    # 1. Setup UI
    if args.no_animate:
        ui.CONFIG["animate"] = False

    ui.print_header()

    # 2. Image Selection
    img_path = None
    if args.input:
        # CLI Argument path
        p = Path(args.input)
        if not p.exists():
            ui.cool_print(f"Error: Input path '{args.input}' does not exist.\n")
            sys.exit(1)
        img_path = p
    else:
        # Interactive Selection
        img_path = image_loader.list_and_select_image()
        if not img_path:
            return  # Exit workflow loop

    # 3. Load Image
    do_preview = not args.no_preview
    img = image_loader.load_image(img_path, preview=do_preview)
    if not img:
        return

    # 4. Determine Dimensions
    target_w, target_h = None, None
    try:
        target_w, target_h = image_resize.calculate_dimensions(
            img, args.width, args.height, args.ratio
        )
    except ValueError as e:
        ui.cool_print(f"Error: {e}\n")
        sys.exit(1)

    # If dimensions not resolved via args, ask interactively
    if target_w is None or target_h is None:
        target_w, target_h = image_resize.interactive_resize(img)

    # 5. Resize
    # Confirm resize if interactive? Old code did.
    # To streamline: if CLI args used, skip confirm. If interactive, show confirm.
    # For now, we follow the "make it work" path.
    img_resized = image_resize.resize_image(img, target_w, target_h)

    if not args.no_preview and (args.width is None and args.height is None):
        # Only show resize confirmation if user was in interactive mode
        ui.cool_print(f"New dimensions: {target_w}x{target_h}. Showing preview...\n")
        img_resized.show()
        ui.cool_print("Is this correct? (y/n): ")
        y = input().strip().lower()
        if not (y == "y" or y == "yes"):
            ui.cool_print("Aborted.\n")
            return

    # 6. Charset
    try:
        chars = charset_mod.get_charset(args.charset)
    except ValueError as e:
        ui.cool_print(f"Error: {e}\n")
        sys.exit(1)

    # 7. Convert
    ui.cool_print("Converting...\n")
    ascii_grid = converter.image_to_ascii(img_resized, chars)

    # 8. Save
    output_path = writer.save_art(ascii_grid, img_path, args.output)
    if not output_path:
        return

    # 9. Server
    # Only run server if we are in interactive mode OR explicitly valid?
    # Old code ran server always.
    ui.clear_terminal()
    server.start_server_and_open_browser(output_path)

    # Wait for server thread interaction
    ui.cool_print("\nServer is running. Check your browser.\n")


def main():
    args = parse_args()

    # Validation: -o should be filename only
    if args.output:
        if os.sep in args.output or "/" in args.output:
            print("Error: Output must be a filename, not a path.")
            sys.exit(1)

    while True:
        process_workflow(args)

        # If CLI args were provided (non-interactive mode), exit after one run
        has_cli_args = any(
            [args.input, args.width, args.height, args.ratio, args.output]
        )
        if has_cli_args:
            break

        ui.cool_print("Enter 1 to run again, or any other key to exit: ")
        choice = input().strip()
        if choice != "1":
            ui.clear_terminal()
            sys.exit()

        ui.clear_terminal()


if __name__ == "__main__":
    main()
