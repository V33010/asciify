# src/ascii_art/terminal.py
import sys
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

from . import charset as charset_mod
from . import converter, image_loader, image_resize, video_renderer, writer

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}


def run_terminal_pipeline(args):
    """
    Main logic for the terminal-first workflow.
    args: The Namespace object from argparse.
    """
    fill = bool(getattr(args, "fill", False))
    fill_hd = bool(getattr(args, "fill_hd", False))

    # --- 1. CHARSET OPERATIONS ---
    if hasattr(args, "show_charsets") and args.show_charsets:
        print("\nAvailable Charsets:")
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

    # --- 1B. FILL MODE FLAG VALIDATION ---
    if fill and fill_hd:
        print("❌ Error: --fill and --fill-hd cannot be used together.")
        sys.exit(1)

    if (fill or fill_hd) and args.charset is not None:
        print("❌ Error: --charset/-c cannot be used with --fill or --fill-hd.")
        sys.exit(1)

    # --- 2. INPUT VALIDATION ---
    if not args.input_file:
        print("Error: Input file is required. Use -i/--input-file <path>")
        sys.exit(1)

    input_str = args.input_file
    is_url = input_str.startswith(("http://", "https://"))

    # Identify if Video
    is_video = False
    if not is_url:
        p = Path(input_str)
        if p.suffix.lower() in VIDEO_EXTENSIONS:
            is_video = True
    else:
        url_path = urlparse(input_str).path.lower()
        if any(url_path.endswith(ext) for ext in VIDEO_EXTENSIONS):
            is_video = True

    # --- 3. VIDEO BRANCH ---
    if is_video:
        # Check for forbidden SAVE flags
        has_save_flag = any(
            [args.save, args.output_folder, args.output_file_name, args.html]
        )

        if has_save_flag:
            print("❌ Error: Saving output is not supported for video files.")
            sys.exit(1)

        # Delegate to video renderer
        video_renderer.play_video(input_str, args)
        return

    # --- 4. IMAGE BRANCH ---
    should_save = any([args.save, args.output_folder, args.output_file_name, args.html])
    if (fill or fill_hd) and should_save and not args.html:
        print(
            "❌ Error: Plain text (.txt) saving is not supported with --fill/--fill-hd. Use --html to save colored fill output."
        )
        sys.exit(1)

    img = None
    original_path_obj = None

    if is_url:
        # Load directly (image_loader handles download)
        img = image_loader.load_image(args.input_file, preview=False)
        if not img:
            sys.exit(1)

        # Recover the filename we extracted during download
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

    # --- 5. CALCULATE DIMENSIONS ---
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

    elif args.downsize is not None:
        try:
            factor = float(args.downsize)
            if factor <= 0:
                raise ValueError
            target_w = int(img.width / factor)
            target_h = int(img.height / factor)
            if target_w < 1 or target_h < 1:
                raise ValueError
        except ValueError:
            print(
                "Error: --downsize must be a positive number that produces non-zero dimensions."
            )
            sys.exit(1)

    else:
        if fill_hd:
            target_w, target_h = image_resize.get_auto_terminal_dimensions_hd(img)
        else:
            target_w, target_h = image_resize.get_auto_terminal_dimensions(img)

    # --- 6. RESIZE ---
    img_resized = image_resize.resize_image(img, target_w, target_h)

    # --- 7. CONVERSION + OUTPUT TO TERMINAL ---
    if fill or fill_hd:
        try:
            if fill_hd:
                output_str = converter.render_fill_hd_image_to_string(img_resized)
            else:
                output_str = converter.render_fill_image_to_string(img_resized)
        except ImportError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

        sys.stdout.write(output_str)

        if should_save:
            img_rgb = (
                img_resized if img_resized.mode == "RGB" else img_resized.convert("RGB")
            )
            writer.save_art(
                np.asarray(img_rgb),
                original_filename=original_path_obj,
                output_folder=args.output_folder,
                output_name=args.output_file_name,
                as_html=True,
                fill_mode="fill_hd" if fill_hd else "fill",
            )
        return

    # --- 8. DETERMINE CHARSET (ASCII/Color modes) ---
    try:
        chars = charset_mod.get_charset(args.charset)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    ascii_grid = None

    if args.color:
        try:
            output_str = converter.render_image_to_string(img_resized, chars)
        except ImportError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

        sys.stdout.write(output_str)

        if should_save:
            ascii_grid = converter.image_to_ascii_with_color(img_resized, chars)
    else:
        try:
            output_str = converter.render_grayscale_image_to_string(
                img_resized,
                chars,
            )
        except ImportError:
            # Keep grayscale terminal output working in Python-only source
            # checkouts where the optional Rust extension is not built.
            ascii_grid = converter.image_to_ascii(img_resized, chars)
            for row in ascii_grid:
                line_parts = [char + " " for char in row]
                sys.stdout.write("".join(line_parts) + "\n")
        else:
            sys.stdout.write(output_str)

            if should_save:
                ascii_grid = converter.image_to_ascii(img_resized, chars)

    # --- 9. SAVE TO FILE (Optional) ---
    if should_save:
        writer.save_art(
            ascii_grid,
            original_filename=original_path_obj,
            output_folder=args.output_folder,
            output_name=args.output_file_name,
            as_html=args.html,
        )
