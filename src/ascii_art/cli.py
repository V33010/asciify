# src/ascii_art/cli.py
import argparse
import os
import sys
from pathlib import Path

from . import charset as charset_mod
from . import (converter, image_loader, image_resize, server, terminal, ui,
               writer)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Asciify: Terminal-first ASCII Art Generator", add_help=True
    )

    # --- INPUT ---
    parser.add_argument("-i", "--input-file", help="Path to input image file")

    # --- MODE SWITCH ---
    parser.add_argument(
        "--full", action="store_true", help="Launch the legacy interactive mode"
    )

    # --- OUTPUT FLAGS ---
    parser.add_argument(
        "-s", "--save", action="store_true", help="Save output to current directory"
    )
    parser.add_argument("--output-folder", help="Specify directory for saved output")
    parser.add_argument(
        "--output-file-name", help="Specify filename (WITHOUT extension)"
    )
    parser.add_argument(
        "--html", action="store_true", help="Save as HTML file (preserves color)"
    )
    parser.add_argument("--color", action="store_true", help="Enable colorized output")

    # --- DIMENSION FLAGS ---
    parser.add_argument("--width", type=int, help="Target width")
    parser.add_argument("--height", type=int, help="Target height")
    parser.add_argument("--aspect-ratio", type=float, help="Target aspect ratio")
    parser.add_argument("--downsize", type=float, help="Downsize factor (n)")

    # --- CHARSET FLAGS ---
    parser.add_argument(
        "--show-charsets", action="store_true", help="List available charsets"
    )
    parser.add_argument("--set-charset", help="Set the default charset for future runs")
    parser.add_argument(
        "-c", "--charset", help="Use a specific charset string for this run"
    )

    # --- LEGACY/FULL MODE ONLY ---
    parser.add_argument(
        "--no-preview", action="store_true", help="Skip preview (Full mode only)"
    )
    parser.add_argument(
        "--no-animate", action="store_true", help="Disable animation (Full mode only)"
    )

    # Parse
    args = parser.parse_args()
    return args


def run_legacy_interactive_mode(args):
    """
    The old interactive workflow for --full flag
    """
    if args.no_animate:
        ui.CONFIG["animate"] = False

    ui.print_header()

    # Image Selection
    img_path = None
    if args.input_file:
        p = Path(args.input_file)
        if not p.exists():
            ui.cool_print(f"Error: Input path '{args.input_file}' does not exist.\n")
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

    # Check flags first, else interactive
    if args.width or args.height:
        try:
            target_w, target_h = image_resize.calculate_dimensions(
                img, args.width, args.height, args.aspect_ratio
            )
        except ValueError as e:
            ui.cool_print(f"Error: {e}\n")
            sys.exit(1)

    if target_w is None or target_h is None:
        target_w, target_h = image_resize.interactive_downsize_factor(img)

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
    output_path = writer.save_art(
        ascii_grid, img_path, output_name=args.output_file_name
    )
    if not output_path:
        return

    # Server
    ui.clear_terminal()
    server.start_server_and_open_browser(output_path)
    ui.cool_print("\nServer is running. Check your browser.\n")


def main():
    args = parse_args()

    # --- 1. CHECK FOR NO ARGS ---
    if len(sys.argv) == 1:
        # "python -m src.ascii_art -> this will DO NOTHING, AND JUST THROW AN ERROR"
        print("Error: No arguments provided.")
        print("Usage: asciify -i <input_file> [options]")
        print("Try 'asciify --help' for details.")
        sys.exit(1)

    # --- 2. BRANCH: FULL INTERACTIVE MODE ---
    if args.full:
        while True:
            run_legacy_interactive_mode(args)
            # Legacy loop logic
            ui.cool_print("Enter 1 to run again, or any other key to exit: ")
            choice = input().strip()
            if choice != "1":
                ui.clear_terminal()
                sys.exit()
            ui.clear_terminal()

    # --- 3. BRANCH: TERMINAL MODE (DEFAULT) ---
    # This handles -i, configuration, printing, and saving
    terminal.run_terminal_pipeline(args)


if __name__ == "__main__":
    main()
