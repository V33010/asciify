# src/ascii_art/video_renderer.py
import queue
import sys
import threading
import time

import cv2
from PIL import Image

from . import charset as charset_mod
from . import converter, image_resize, ui

# Import Rust renderer
try:
    from .ascii_art_rs import (
        render_fill_diff_to_string,
        render_fill_hd_diff_to_string,
        render_fill_hd_to_string,
        render_fill_to_string,
        render_frame_to_string,
        render_grayscale_to_string,
        reset_diff_state,
    )
except ImportError:
    render_fill_diff_to_string = None
    render_fill_hd_diff_to_string = None
    render_fill_hd_to_string = None
    render_fill_to_string = None
    render_frame_to_string = None
    render_grayscale_to_string = None
    reset_diff_state = None

# Keep references to the original Rust callables so tests that monkeypatch
# render_fill_to_string / render_fill_hd_to_string continue to intercept calls.
_ORIG_RENDER_FILL = render_fill_to_string
_ORIG_RENDER_FILL_HD = render_fill_hd_to_string

_SENTINEL = object()


class _FramePrefetcher:
    """Background producer that decodes, resizes, and color-converts video frames.

    Because OpenCV's ``cap.read()``, ``cv2.resize()``, and ``cv2.cvtColor()``
    release the Python GIL, running them on a worker thread overlaps decoding
    frame N+1 with rendering, terminal I/O, and pacing for frame N.
    """

    def __init__(self, cap, target_w, target_h, needs_rgb, maxsize=2):
        self._cap = cap
        self._target_w = target_w
        self._target_h = target_h
        self._needs_rgb = needs_rgb
        self._queue = queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="asciify-video-prefetch", daemon=True
        )

    def start(self):
        self._thread.start()
        return self

    def _run(self):
        try:
            while not self._stop.is_set():
                ret, frame = self._cap.read()
                if not ret:
                    break

                frame_resized = image_resize.resize_video_frame(
                    frame,
                    self._target_w,
                    self._target_h,
                )
                if self._needs_rgb:
                    frame_ready = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                else:
                    frame_ready = frame_resized

                while not self._stop.is_set():
                    try:
                        self._queue.put(frame_ready, timeout=0.05)
                        break
                    except queue.Full:
                        continue
        finally:
            # Always signal EOF so the consumer never blocks forever.
            while True:
                try:
                    self._queue.put(_SENTINEL, timeout=0.05)
                    break
                except queue.Full:
                    if self._stop.is_set():
                        try:
                            self._queue.get_nowait()
                        except queue.Empty:
                            pass

    def get(self):
        item = self._queue.get()
        return None if item is _SENTINEL else item

    def get_nowait_if_available(self):
        """Non-blocking pop used when dropping stale frames to catch up."""
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return False, None
        if item is _SENTINEL:
            return True, None
        return True, item

    def stop(self):
        self._stop.set()
        # Drain any pending item so the producer thread can exit immediately.
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._thread.join(timeout=1.0)


def _prepare_frame(frame, target_w, target_h, needs_rgb):
    frame_resized = image_resize.resize_video_frame(frame, target_w, target_h)
    if needs_rgb:
        return cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
    return frame_resized


def play_video(filepath, args):
    """
    Plays a video file as ASCII art in the terminal.
    """
    fill = bool(getattr(args, "fill", False))
    fill_hd = bool(getattr(args, "fill_hd", False))

    if fill and fill_hd:
        print("❌ Error: --fill and --fill-hd cannot be used together.")
        return

    if (fill or fill_hd) and getattr(args, "charset", None) is not None:
        print("❌ Error: --charset/-c cannot be used with --fill or --fill-hd.")
        return

    needs_rgb = bool(args.color or fill or fill_hd)

    cap = cv2.VideoCapture(str(filepath))
    if not cap.isOpened():
        print(f"❌ Error: Could not open video file '{filepath}'.")
        return

    prefetcher = None
    cursor_hidden = False

    try:
        # 1. Get Video Properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0
        frame_delay = 1.0 / fps

        # 2. Decode the first frame (used for dimensions AND rendered as frame 0).
        ret, first_frame = cap.read()
        if not ret:
            print("❌ Error: Video is empty or unreadable.")
            return

        if needs_rgb:
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
            if fill_hd:
                target_w, target_h = image_resize.get_auto_terminal_dimensions_hd(
                    pil_img
                )
            else:
                target_w, target_h = image_resize.get_auto_terminal_dimensions(pil_img)

        # Determine Charset (not used in fill modes)
        chars_str = None
        chars_list = None
        if not (fill or fill_hd):
            try:
                chars_str = charset_mod.get_charset(args.charset)
                chars_list = list(chars_str)
            except ValueError as e:
                print(f"Error: {e}")
                return

        # Select differential Rust renderer when available and not overridden
        use_fill_hd_diff = (
            fill_hd
            and render_fill_hd_diff_to_string is not None
            and render_fill_hd_to_string is _ORIG_RENDER_FILL_HD
        )
        use_fill_diff = (
            fill
            and render_fill_diff_to_string is not None
            and render_fill_to_string is _ORIG_RENDER_FILL
        )

        # Check for Rust support
        if fill_hd and not use_fill_hd_diff and render_fill_hd_to_string is None:
            print(
                "❌ Error: Rust extension not found. Build with 'maturin develop'."
            )
            return
        if fill and not use_fill_diff and render_fill_to_string is None:
            print(
                "❌ Error: Rust extension not found. Build with 'maturin develop'."
            )
            return
        if args.color and not (fill or fill_hd) and render_frame_to_string is None:
            print(
                "❌ Error: Rust extension not found. Build with 'maturin develop'."
            )
            return

        if (use_fill_diff or use_fill_hd_diff) and reset_diff_state is not None:
            reset_diff_state()

        ui.clear_terminal()
        ui.hide_cursor()
        cursor_hidden = True

        # Prepare frame 0 and start background decode/resize thread for frames 1+.
        frame_for_render = _prepare_frame(first_frame, target_w, target_h, needs_rgb)
        prefetcher = _FramePrefetcher(
            cap, target_w, target_h, needs_rgb, maxsize=2
        ).start()

        next_frame_at = time.monotonic() + frame_delay

        while True:
            if use_fill_hd_diff:
                # Differential renderer already embeds DEC 2026 sync markers.
                output_str = render_fill_hd_diff_to_string(frame_for_render)
                if output_str:
                    sys.stdout.write(output_str)
                    sys.stdout.flush()

            elif use_fill_diff:
                output_str = render_fill_diff_to_string(frame_for_render)
                if output_str:
                    sys.stdout.write(output_str)
                    sys.stdout.flush()

            else:
                if fill_hd:
                    body = render_fill_hd_to_string(frame_for_render)
                elif fill:
                    body = render_fill_to_string(frame_for_render)
                elif args.color:
                    body = render_frame_to_string(frame_for_render, chars_list)
                elif render_grayscale_to_string is not None:
                    body = render_grayscale_to_string(frame_for_render, chars_list)
                else:
                    pil_frame = Image.fromarray(frame_for_render)
                    ascii_grid = converter.image_to_ascii(pil_frame, chars_str)
                    body = "\n".join(
                        "".join(char + " " for char in row) for row in ascii_grid
                    )

                # Single atomic write wrapped in DEC Mode 2026 synchronized output.
                sys.stdout.write(f"{ui.SYNC_START}{ui.CURSOR_HOME}{body}{ui.SYNC_END}")
                sys.stdout.flush()

            # Deadline-based pacing (accounts for decode + render + PTY write).
            now = time.monotonic()
            sleep_time = next_frame_at - now
            if sleep_time > 0:
                time.sleep(sleep_time)
                next_frame_at += frame_delay
            else:
                # Behind schedule: still yield briefly and drop stale queued
                # frames if more than one full frame behind to stay in sync.
                time.sleep(0)
                if now - next_frame_at > frame_delay:
                    while now - next_frame_at > frame_delay:
                        popped, dropped = prefetcher.get_nowait_if_available()
                        if not popped:
                            next_frame_at = now + frame_delay
                            break
                        if dropped is None:
                            # Hit EOF while catching up.
                            frame_for_render = None
                            break
                        next_frame_at += frame_delay
                    if frame_for_render is None:
                        break
                else:
                    next_frame_at += frame_delay

            frame_for_render = prefetcher.get()
            if frame_for_render is None:
                break

    except KeyboardInterrupt:
        ui.clear_terminal()
        print("\nStopped.")

    finally:
        if prefetcher is not None:
            prefetcher.stop()
        if (fill or fill_hd) and reset_diff_state is not None:
            reset_diff_state()
        if cursor_hidden:
            ui.show_cursor()
        cap.release()
