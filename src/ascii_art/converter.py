# src/ascii_art/converter.py
import numpy as np


def image_to_ascii(img, charset):
    """
    Converts a PIL image to a 2D list of characters (Grayscale).
    """
    arr = np.array(img)

    # Handle dimensions (Height, Width)
    # Convert to grayscale logic: max(R, G, B)
    if len(arr.shape) == 3:
        # Vectorized operation: max across channel axis (axis 2)
        gray_arr = np.max(arr[:, :, :3], axis=2)
    else:
        gray_arr = arr

    # Normalize to charset length
    scale = (len(charset) - 1) / 255
    indices = (gray_arr * scale).astype(int)

    # Map indices to characters
    ascii_grid = []
    for row in indices:
        ascii_row = [charset[i] for i in row]
        ascii_grid.append(ascii_row)

    return ascii_grid


def image_to_ascii_with_color(img, charset):
    """
    Converts a PIL image to a 2D list of tuples: (character, (r, g, b)).
    """
    # Ensure image is RGB to guarantee 3 channels
    img_rgb = img.convert("RGB")
    arr = np.array(img_rgb)

    # 1. Get Grayscale values for Char selection
    gray_arr = np.max(arr, axis=2)

    # 2. Normalize for charset index
    scale = (len(charset) - 1) / 255
    indices = (gray_arr * scale).astype(int)

    # 3. Build the grid
    # This results in a list of rows, where each item is (char, (r,g,b))
    colored_grid = []

    rows, cols, _ = arr.shape

    for i in range(rows):
        row_data = []
        for j in range(cols):
            char_idx = indices[i, j]
            char = charset[char_idx]
            rgb = tuple(arr[i, j])  # (R, G, B)
            row_data.append((char, rgb))
        colored_grid.append(row_data)

    return colored_grid
