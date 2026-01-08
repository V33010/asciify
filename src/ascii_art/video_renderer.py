# src/ascii_art/video_renderer.py
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from . import charset as charset_mod
from . import image_resize, ui

# Import Rust renderer
try:
    from .ascii_art_rs import render_frame_to_string
except ImportError:
    render_frame_to_string = None


def play_video(filepath, args):
    """
    Plays a video file as ASCII art in the terminal.
    """
    # 1. Open Video
    cap = cv2.VideoCapture(str(filepath))
    if not cap.isOpened():
        print(f"❌ Error: Could not open video file '{filepath}'.")
        return

    # 2. Get Video Properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0  # Fallback
    frame_delay = 1.0 / fps

    # 3. Setup Logic (Dimensions & Charset)
    ret, first_frame = cap.read()
    if not ret:
        print("❌ Error: Video is empty or unreadable.")
        return

    first_frame_rgb = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(first_frame_rgb)

    # Determine Dimensions
    target_w, target_h = None, None
    if args.width or args.height:
        try:
            target_w, target_h = image_resize.calculate_dimensions(
                pil_img, args.width, args.height, args.aspect_ratio
            )
        except ValueError as e:
            print(f"Error: {e}")
            return
    elif args.downsize:
        try:
            factor = float(args.downsize)
            target_w = int(pil_img.width / factor)
            target_h = int(pil_img.height / factor)
        except ValueError:
            print("Error: --downsize must be a positive number.")
            return
    else:
        target_w, target_h = image_resize.get_auto_terminal_dimensions(pil_img)

    # Determine Charset
    try:
        chars_str = charset_mod.get_charset(args.charset)
        # Rust requires a List[str], not a single str
        chars_list = list(chars_str)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Check for Rust support
    if args.color and render_frame_to_string is None:
        print("❌ Error: Rust extension not found. Build with 'maturin develop'.")
        return

    # Clear screen ONCE before starting
    ui.clear_terminal()

    try:
        while True:
            start_time = time.time()

            ret, frame = cap.read()
            if not ret:
                break  # End of video

            # Resize Frame (OpenCV is faster than PIL here, stay in CV2/NumPy land)
            # OpenCV expects (width, height)
            frame_resized = cv2.resize(
                frame, (target_w, target_h), interpolation=cv2.INTER_AREA
            )

            # Convert BGR (OpenCV) to RGB (Standard)
            # We pass this numpy array directly to Rust
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

            # RENDER FRAME
            ui.move_cursor_home()

            if args.color:
                # --- NEW RUST PATH ---
                # Returns one giant string with all ANSI codes
                output_str = render_frame_to_string(frame_rgb, chars_list)
                sys.stdout.write(output_str)
            else:
                # --- LEGACY GRAYSCALE PATH (Keep Python/NumPy) ---
                # Since we optimized COLOR, let's rely on the old converter for grayscale
                pil_frame = Image.fromarray(frame_rgb)
                from . import converter

                ascii_grid = converter.image_to_ascii(pil_frame, chars_str)

                output_buffer = []
                for row in ascii_grid:
                    # Grayscale aspect ratio fix
                    row_parts = [char + " " for char in row]
                    output_buffer.append("".join(row_parts))
                sys.stdout.write("\n".join(output_buffer))

            sys.stdout.flush()

            # TIMING CONTROL
            process_time = time.time() - start_time
            sleep_time = max(0, frame_delay - process_time)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        ui.clear_terminal()
        print("\nStopped.")
    finally:
        cap.release()
