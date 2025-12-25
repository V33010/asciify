# src/ascii_art/cli.py
import argparse
import os
import sys
from pathlib import Path

from . import charset as charset_mod
from . import terminal  # Imported the new module
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

    # New Color Flag
    parser.add_argument(
        "--color",
        action="store_true",
        help="Enable colorized output (only works with --terminal)",
    )

    return parser.parse_args()


def process_workflow(args):
    # --- TERMINAL MODE PATH ---
    if args.terminal:
        terminal.run_terminal_mode(args.terminal, args.charset, args.color)
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
