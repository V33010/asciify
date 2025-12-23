# src/ascii_art/image_resize.py
from PIL import Image

from .ui import clear_terminal, cool_print


def calculate_dimensions(img, target_w=None, target_h=None, ratio=None):
    """
    Calculates new dimensions based on inputs and constraints.
    """
    orig_w, orig_h = img.size
    orig_ratio = orig_w / orig_h

    # Validation: Logic Check for conflicting arguments
    if target_w and target_h and ratio:
        calc_ratio = target_w / target_h
        # Allow a small float margin of error
        if abs(calc_ratio - ratio) > 0.01:
            raise ValueError(
                f"Conflict: Width ({target_w}) and Height ({target_h}) imply ratio {calc_ratio:.2f}, but --ratio {ratio} was provided."
            )

    if target_w and target_h:
        return target_w, target_h

    if target_w:
        # Calculate H based on ratio
        r = ratio if ratio else orig_ratio
        return target_w, int(target_w / r)

    if target_h:
        # Calculate W based on ratio
        r = ratio if ratio else orig_ratio
        return int(target_h * r), target_h

    # If nothing provided, return None to trigger interactive mode or default
    return None, None


def resize_image(img, width, height):
    """
    Resizes image using LANCZOS filter.
    """
    return img.resize((width, height), Image.Resampling.LANCZOS)


def interactive_resize(img):
    """
    Asks user for dimensions interactively.
    """
    cool_print(f"\nCurrent dimensions: {img.size}\n")
    cool_print("Enter new dimensions (keep largest below 180 recommended).\n")

    while True:
        try:
            cool_print("Enter width: ")
            w = int(input())
            cool_print("Enter height: ")
            h = int(input())
            return w, h
        except ValueError:
            cool_print("Invalid number. Please try again.\n")
