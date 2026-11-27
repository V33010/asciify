# src/ascii_art/video_renderer.py
import sys
import time

import cv2
from PIL import Image

from . import charset as charset_mod
from . import converter, image_resize, ui

# Import Rust renderer
try:
    from .ascii_art_rs import render_frame_to_string, render_grayscale_to_string
except ImportError:
    render_frame_to_string = None
    render_grayscale_to_string = None


def play_video(filepath, args):
    """
    Plays a video file as ASCII art in the terminal.
    """
    cap = cv2.VideoCapture(str(filepath))
    if not cap.isOpened():
        print(f"❌ Error: Could not open video file '{filepath}'.")
        return

    try:
        # 1. Get Video Properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0
        frame_delay = 1.0 / fps

        # 2. Decode the first frame.
        # This frame is also rendered below; it isn't discarded.
        ret, first_frame = cap.read()
        if not ret:
            print("❌ Error: Video is empty or unreadable.")
            return

        if args.color:
            first_frame_for_dimensions = cv2.cvtColor(
                first_frame,
                cv2.COLOR_BGR2RGB,
            )
        else:
            # Grayscale conversion uses max(B, G, R), so channel order is
            # irrelevant. Keep OpenCV's native BGR frame and avoid a full
            # frame BGR -> RGB conversion.
            first_frame_for_dimensions = first_frame

        pil_img = Image.fromarray(first_frame_for_dimensions)

        # Determine Dimensions
        target_w, target_h = None, None

        if args.width or args.height:
            try:
                target_w, target_h = image_resize.calculate_dimensions(
                    pil_img,
                    args.width,
                    args.height,
                    args.aspect_ratio,
                )
            except ValueError as e:
                print(f"Error: {e}")
                return

        elif args.downsize is not None:
            try:
                factor = float(args.downsize)

                if factor <= 0:
                    raise ValueError

                target_w = int(pil_img.width / factor)
                target_h = int(pil_img.height / factor)

                if target_w < 1 or target_h < 1:
                    raise ValueError

            except ValueError:
                print(
                    "Error: --downsize must be a positive number "
                    "that produces non-zero dimensions."
                )
                return

        else:
            target_w, target_h = image_resize.get_auto_terminal_dimensions(pil_img)

        # Determine Charset
        try:
            chars_str = charset_mod.get_charset(args.charset)
            chars_list = list(chars_str)
        except ValueError as e:
            print(f"Error: {e}")
            return

        # Check for Rust support
        if args.color and render_frame_to_string is None:
            print(
                "❌ Error: Rust extension not found. Build with 'maturin develop'."
            )
            return

        ui.clear_terminal()

        # Render the first frame that was already decoded.
        frame = first_frame

        while True:
            start_time = time.monotonic()

            frame_resized = image_resize.resize_video_frame(
                frame,
                target_w,
                target_h,
            )

            if args.color:
                frame_for_render = cv2.cvtColor(
                    frame_resized,
                    cv2.COLOR_BGR2RGB,
                )
            else:
                # Grayscale conversion uses max(B, G, R), so BGR is already
                # in the correct representation for this operation.
                frame_for_render = frame_resized

            ui.move_cursor_home()

            if args.color:
                output_str = render_frame_to_string(
                    frame_for_render,
                    chars_list,
                )
                sys.stdout.write(output_str)

            elif render_grayscale_to_string is not None:
                # Rust performs both grayscale character mapping and terminal
                # formatting directly from the resized OpenCV BGR frame.
                output_str = render_grayscale_to_string(
                    frame_for_render,
                    chars_list,
                )
                sys.stdout.write(output_str)

            else:
                # Python fallback for source checkouts without the optional
                # Rust extension.
                pil_frame = Image.fromarray(frame_for_render)

                ascii_grid = converter.image_to_ascii(
                    pil_frame,
                    chars_str,
                )

                output_buffer = []

                for row in ascii_grid:
                    row_parts = [char + " " for char in row]
                    output_buffer.append("".join(row_parts))

                sys.stdout.write("\n".join(output_buffer))

            sys.stdout.flush()

            process_time = time.monotonic() - start_time
            sleep_time = max(0, frame_delay - process_time)
            time.sleep(sleep_time)

            # Only now read the next frame.
            ret, frame = cap.read()

            if not ret:
                break

    except KeyboardInterrupt:
        ui.clear_terminal()
        print("\nStopped.")

    finally:
        cap.release()
