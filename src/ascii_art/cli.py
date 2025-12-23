# src/ascii_art/cli.py
import argparse
import os
import sys
from pathlib import Path

from . import charset as charset_mod
from . import converter, image_loader, image_resize, server, ui, writer


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert images to ASCII art", add_help=False
    )

    parser.add_argument("--help", action="help", help="Show this help message and exit")

    parser.add_argument("-i", "--input", help="Path to input image")
    parser.add_argument("-o", "--output", help="Output filename (no extension)")
    parser.add_argument("-c", "--charset", help="Custom charset string")
    parser.add_argument("--no-preview", action="store_true", help="Skip image preview")
    parser.add_argument(
        "--no-animate", action="store_true", help="Disable text animation"
    )

    # Dimension arguments
    parser.add_argument("-w", "--width", type=int, help="Target width")
    parser.add_argument("-h", "--height", type=int, help="Target height")
    parser.add_argument("--ratio", type=float, help="Target aspect ratio")

    # New Flag
    parser.add_argument(
        "--bypass-downsizing",
        action="store_true",
        help="Allow downsize ratio < 1 (upscaling)",
    )

    return parser.parse_args()


def process_workflow(args):
    # 1. Setup UI
    if args.no_animate:
        ui.CONFIG["animate"] = False

    ui.print_header()

    # 2. Image Selection
    img_path = None
    if args.input:
        p = Path(args.input)
        if not p.exists():
            ui.cool_print(f"Error: Input path '{args.input}' does not exist.\n")
            sys.exit(1)
        img_path = p
    else:
        img_path = image_loader.list_and_select_image()
        if not img_path:
            return

    # 3. Load Image
    do_preview = not args.no_preview
    img = image_loader.load_image(img_path, preview=do_preview)
    if not img:
        return

    # 4. Determine Dimensions
    target_w, target_h = None, None

    # Check if user provided explicit dimensions via flags
    try:
        target_w, target_h = image_resize.calculate_dimensions(
            img, args.width, args.height, args.ratio
        )
    except ValueError as e:
        ui.cool_print(f"Error: {e}\n")
        sys.exit(1)

    # If NOT provided via flags, use the new Interactive Downsize Workflow
    if target_w is None or target_h is None:
        target_w, target_h = image_resize.interactive_downsize_factor(
            img, args.bypass_downsizing
        )

    # 5. Resize
    # We don't need to show a confirmation preview for this anymore
    # because the math is predictable (Just dividing by n).
    img_resized = image_resize.resize_image(img, target_w, target_h)

    # 6. Charset
    try:
        chars = charset_mod.get_charset(args.charset)
    except ValueError as e:
        ui.cool_print(f"Error: {e}\n")
        sys.exit(1)

    # 7. Convert
    ui.cool_print(f"Converting to {target_w}x{target_h}...\n")
    ascii_grid = converter.image_to_ascii(img_resized, chars)

    # 8. Save
    output_path = writer.save_art(ascii_grid, img_path, args.output)
    if not output_path:
        return

    # 9. Server
    ui.clear_terminal()
    server.start_server_and_open_browser(output_path)

    ui.cool_print("\nServer is running. Check your browser.\n")


def main():
    args = parse_args()

    if args.output:
        if os.sep in args.output or "/" in args.output:
            print("Error: Output must be a filename, not a path.")
            sys.exit(1)

    while True:
        process_workflow(args)

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
