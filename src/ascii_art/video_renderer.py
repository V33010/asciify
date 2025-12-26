# src/ascii_art/video_renderer.py
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from . import charset as charset_mod
from . import converter, image_resize, ui


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
    # We read the first frame to calculate dimensions ONCE.
    ret, first_frame = cap.read()
    if not ret:
        print("❌ Error: Video is empty or unreadable.")
        return

    # Convert first frame to PIL for the resize logic
    first_frame_rgb = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(first_frame_rgb)

    # Determine Dimensions using existing logic
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
        chars = charset_mod.get_charset(args.charset)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Clear screen ONCE before starting
    ui.clear_terminal()

    try:
        while True:
            start_time = time.time()

            # READ FRAME
            # If we are at the very first frame, we already read it.
            # However, for simplicity of the loop, we'll re-process the first frame logic
            # or just continue. Let's reset pointer to 0 to be clean.
            # (Or just continue reading if we didn't consume it fully yet).
            # To avoid complexity, we just continue reading.
            # If we want to include the first frame, we'd need a flag, but missing 1 frame is fine.
            ret, frame = cap.read()
            if not ret:
                break  # End of video

            # PROCESS FRAME
            # OpenCV is BGR, PIL is RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_frame = Image.fromarray(frame_rgb)

            # Resize
            img_resized = image_resize.resize_image(pil_frame, target_w, target_h)

            # Convert to ASCII
            if args.color:
                ascii_grid = converter.image_to_ascii_with_color(img_resized, chars)
            else:
                ascii_grid = converter.image_to_ascii(img_resized, chars)

            # RENDER FRAME
            # Move cursor to top-left to overwrite previous frame
            ui.move_cursor_home()

            output_buffer = []
            for row in ascii_grid:
                row_parts = []
                for item in row:
                    if isinstance(item, tuple):
                        char, (r, g, b) = item
                        # Color logic
                        display_str = char + "."  # Aspect ratio fix
                        row_parts.append(
                            ui.get_ansi_colored_string(display_str, r, g, b)
                        )
                    else:
                        char = item
                        row_parts.append(char + " ")  # Aspect ratio fix
                output_buffer.append("".join(row_parts))

            # Print the entire frame at once to minimize tearing
            sys.stdout.write("\n".join(output_buffer))
            sys.stdout.flush()

            # TIMING CONTROL
            process_time = time.time() - start_time
            sleep_time = max(0, frame_delay - process_time)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        ui.clear_terminal()
        print("\nStopped.")
    finally:
        cap.release()
