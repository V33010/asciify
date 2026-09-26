# src/ascii_art/converter.py
import numpy as np

# Try to import the Rust extension.
try:
    from .ascii_art_rs import (
        image_to_ascii_rs,
        render_frame_to_string,
        render_grayscale_to_string,
    )
except ImportError:
    image_to_ascii_rs = None
    render_frame_to_string = None
    render_grayscale_to_string = None


def image_to_ascii(img, charset):
    """
    Converts a PIL image to a 2D list of characters (Grayscale).
    """
    arr = np.array(img)

    # Handle dimensions (Height, Width)
    if len(arr.shape) == 3:
        gray_arr = np.max(arr[:, :, :3], axis=2)
    else:
        gray_arr = arr

    scale = (len(charset) - 1) / 255
    indices = (gray_arr * scale).astype(int)

    ascii_grid = []
    for row in indices:
        ascii_row = [charset[i] for i in row]
        ascii_grid.append(ascii_row)

    return ascii_grid


def render_image_to_string(img, charset):
    """Render a color PIL image directly to one ANSI string in Rust.

    The terminal color path does not need the intermediate
    ``[(character, (r, g, b)), ...]`` Python grid, so send the RGB pixel
    array straight to Rust, which builds the complete TrueColor ANSI output
    string in one pass.
    """
    if render_frame_to_string is None:
        raise ImportError(
            "Rust extension 'ascii_art_rs' not found. Please build with 'maturin develop'."
        )

    img_rgb = img if img.mode == "RGB" else img.convert("RGB")
    arr = np.asarray(img_rgb)
    return render_frame_to_string(arr, list(charset))


def render_grayscale_image_to_string(img, charset):
    """Render a grayscale PIL image directly to one ASCII string in Rust.

    The grayscale mapping is based on the maximum of the RGB channels, so
    channel order does not matter. Rust performs both the pixel-to-charset
    conversion and the terminal-width formatting, avoiding Python per-pixel
    work on the terminal path.
    """
    if render_grayscale_to_string is None:
        raise ImportError(
            "Rust extension 'ascii_art_rs' not found. Please build with 'maturin develop'."
        )

    if not charset:
        raise ValueError("Charset must be a non-empty string.")

    img_rgb = img if img.mode == "RGB" else img.convert("RGB")
    arr = np.asarray(img_rgb)
    return render_grayscale_to_string(arr, list(charset))


def image_to_ascii_with_color(img, charset):
    """
    Converts a PIL image to a 2D list of tuples: (character, (r, g, b)).
    NOW ACCELERATED BY RUST (Target A).
    """
    if image_to_ascii_rs is None:
        raise ImportError(
            "Rust extension 'ascii_art_rs' not found. Please build with 'maturin develop'."
        )

    # Ensure image is RGB to guarantee 3 channels
    img_rgb = img.convert("RGB")
    arr = np.array(img_rgb)

    # Convert the string "abc" into a list ["a", "b", "c"]
    # Rust expects a Vec<String>, so we must provide a Python List of strings.
    charset_list = list(charset)

    # Pass the heavy lifting to Rust
    return image_to_ascii_rs(arr, charset_list)
