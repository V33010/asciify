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

    parser.add_argument("-w", "--width", type=int, help="Target width")
    parser.add_argument("-h", "--height", type=int, help="Target height")
    parser.add_argument("--ratio", type=float, help="Target aspect ratio")

    parser.add_argument(
        "--bypass-downsizing",
        action="store_true",
        help="Allow downsize ratio < 1 (upscaling)",
    )

    # New Terminal Mode Argument
    parser.add_argument(
        "-t",
        "--terminal",
        help="Run in headless terminal mode with provided image path",
    )

    return parser.parse_args()


def process_workflow(args):
    # --- TERMINAL MODE PATH ---
    if args.terminal:
        # 1. Validate Input
        p = Path(args.terminal)
        if not p.exists():
            print(f"Error: File '{args.terminal}' not found.")
            sys.exit(1)

        # 2. Load Image (No Previews, No "Smart Open")
        # We use strict loading because we are likely in a headless env
        img = image_loader.load_image(p, preview=False)
        if not img:
            sys.exit(1)

        # 3. Auto-Calculate Sensible Dimensions
        target_w, target_h = image_resize.get_auto_terminal_dimensions(img)

        # 4. Resize
        img_resized = image_resize.resize_image(img, target_w, target_h)

        # 5. Get Charset
        try:
            chars = charset_mod.get_charset(args.charset)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

        # 6. Convert
        ascii_grid = converter.image_to_ascii(img_resized, chars)

        # 7. Soft Clear & Print
        ui.soft_clear()

        # Print row by row
        for row in ascii_grid:
            # Note: We usually add a space in writer.py, but for direct terminal view
            # without saving to file, simpler is often better.
            # However, to keep consistency with the 'Square' look:
            sys.stdout.write("".join([char + " " for char in row]) + "\n")
            # sys.stdout.write(
            #     "".join([char + "" for char in row]) + "\n"
            # )  # test without space
            # sys.stdout.write(
            #     "".join([char + char for char in row]) + "\n"
            # )  # test 2 characters
            # sys.stdout.write("".join([char + "ˑ" for char in row]) + "\n")  # test .

        return  # Exit workflow immediately

    # --- STANDARD INTERACTIVE / CLI PATH ---
    if args.no_animate:
        ui.CONFIG["animate"] = False

    ui.print_header()

    # Image Selection
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

    # Load Image
    do_preview = not args.no_preview
    img = image_loader.load_image(img_path, preview=do_preview)
    if not img:
        return

    # Dimensions
    target_w, target_h = None, None
    try:
        target_w, target_h = image_resize.calculate_dimensions(
            img, args.width, args.height, args.ratio
        )
    except ValueError as e:
        ui.cool_print(f"Error: {e}\n")
        sys.exit(1)

    if target_w is None or target_h is None:
        target_w, target_h = image_resize.interactive_downsize_factor(
            img, args.bypass_downsizing
        )

    # Resize
    img_resized = image_resize.resize_image(img, target_w, target_h)

    # Charset
    try:
        chars = charset_mod.get_charset(args.charset)
    except ValueError as e:
        ui.cool_print(f"Error: {e}\n")
        sys.exit(1)

    # Convert
    ui.cool_print(f"Converting to {target_w}x{target_h}...\n")
    ascii_grid = converter.image_to_ascii(img_resized, chars)

    # Save
    output_path = writer.save_art(ascii_grid, img_path, args.output)
    if not output_path:
        return

    # Server
    ui.clear_terminal()
    server.start_server_and_open_browser(output_path)

    ui.cool_print("\nServer is running. Check your browser.\n")


def main():
    args = parse_args()

    if args.output and (os.sep in args.output or "/" in args.output):
        print("Error: Output must be a filename, not a path.")
        sys.exit(1)

    while True:
        process_workflow(args)

        # If Terminal Mode OR CLI args provided, exit after one run
        has_cli_args = any(
            [
                args.input,
                args.width,
                args.height,
                args.ratio,
                args.output,
                args.terminal,
            ]
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
