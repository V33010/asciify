# src/ascii_art/converter.py
import numpy as np

# Try to import the Rust extension.
try:
    from .ascii_art_rs import image_to_ascii_rs
except ImportError:
    image_to_ascii_rs = None


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
