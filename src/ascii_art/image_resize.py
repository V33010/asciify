# src/ascii_art/image_resize.py
from PIL import Image

from .ui import cool_print


def calculate_dimensions(img, target_w=None, target_h=None, ratio=None):
    """
    Calculates dimensions if CLI args (width/height) are provided.
    Returns (None, None) if no args are present.
    """
    orig_w, orig_h = img.size
    orig_ratio = orig_w / orig_h

    if target_w and target_h and ratio:
        calc_ratio = target_w / target_h
        if abs(calc_ratio - ratio) > 0.01:
            raise ValueError(
                f"Conflict: Width ({target_w}) and Height ({target_h}) imply ratio {calc_ratio:.2f}, but --ratio {ratio} was provided."
            )

    if target_w and target_h:
        return target_w, target_h

    if target_w:
        r = ratio if ratio else orig_ratio
        return target_w, int(target_w / r)

    if target_h:
        r = ratio if ratio else orig_ratio
        return int(target_h * r), target_h

    return None, None


def resize_image(img, width, height):
    """
    Resizes image using LANCZOS filter.
    """
    return img.resize((width, height), Image.Resampling.LANCZOS)


def interactive_downsize_factor(img, bypass_downsizing=False):
    """
    Asks user for a downsize factor 'n'.
    New dimensions = Original / n.
    """
    orig_w, orig_h = img.size
    cool_print(f"\nOriginal dimensions: {orig_w}x{orig_h}\n")

    while True:
        cool_print("Enter downsize factor 'n' (New size = Original / n): ")
        try:
            val = input().strip()
            n = float(val)

            # Validation Logic
            if bypass_downsizing:
                if n <= 0:
                    cool_print("Factor 'n' must be > 0. Try again.\n")
                    continue
            else:
                if n < 1:
                    cool_print("Factor 'n' must be >= 1 (Downsizing only).\n")
                    cool_print("Use --bypass-downsizing flag to allow upscaling.\n")
                    continue

            # Calculate new dimensions
            new_w = int(orig_w / n)
            new_h = int(orig_h / n)

            # Safety check to prevent 0px images
            if new_w < 1 or new_h < 1:
                cool_print(
                    f"Resulting image ({new_w}x{new_h}) is too small! Use a smaller 'n'.\n"
                )
                continue

            cool_print(f"Calculated dimensions: {new_w}x{new_h}\n")
            return new_w, new_h

        except ValueError:
            cool_print("Invalid number. Please enter a number (e.g. 2, 4, 10).\n")
