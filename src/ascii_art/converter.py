# src/ascii_art/converter.py
import numpy as np


def image_to_ascii(img, charset):
    """
    Converts a PIL image to a 2D list of characters.
    """
    # Convert to numpy array
    arr = np.array(img)

    # Handle dimensions (Height, Width)
    height, width = arr.shape[0], arr.shape[1]

    # Convert to grayscale logic: max(R, G, B)
    # Check if image has 3 channels (RGB) or 4 (RGBA)
    if len(arr.shape) == 3:
        # Vectorized operation is much faster than nested loops
        # Taking max across channel axis (axis 2)
        gray_arr = np.max(arr[:, :, :3], axis=2)
    else:
        # Already grayscale
        gray_arr = arr

    # Normalize to charset length
    # Pixel 0-255 -> Index 0-(len(charset)-1)
    scale = (len(charset) - 1) / 255
    indices = (gray_arr * scale).astype(int)

    # Map indices to characters
    # We can use numpy lookup, but list comprehension is clear here
    ascii_grid = []
    for row in indices:
        ascii_row = [charset[i] for i in row]
        ascii_grid.append(ascii_row)

    return ascii_grid
