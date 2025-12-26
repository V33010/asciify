# src/ascii_art/image_resize.py
import shutil

from PIL import Image

from .ui import cool_print


def calculate_dimensions(img, target_w=None, target_h=None, ratio=None):
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
    return img.resize((width, height), Image.Resampling.LANCZOS)


def interactive_downsize_factor(img, bypass_downsizing=False):
    orig_w, orig_h = img.size
    cool_print(f"\nOriginal dimensions: {orig_w}x{orig_h}\n")

    while True:
        cool_print("Enter downsize factor 'n' (New size = Original / n): ")
        try:
            val = input().strip()
            n = float(val)

            if bypass_downsizing:
                if n <= 0:
                    cool_print("Factor 'n' must be > 0. Try again.\n")
                    continue
            else:
                if n < 1:
                    cool_print("Factor 'n' must be >= 1 (Downsizing only).\n")
                    cool_print("Use --bypass-downsizing flag to allow upscaling.\n")
                    continue

            new_w = int(orig_w / n)
            new_h = int(orig_h / n)

            if new_w < 1 or new_h < 1:
                cool_print(
                    f"Resulting image ({new_w}x{new_h}) is too small! Use a smaller 'n'.\n"
                )
                continue

            cool_print(f"Calculated dimensions: {new_w}x{new_h}\n")
            return new_w, new_h

        except ValueError:
            cool_print("Invalid number. Please enter a number (e.g. 2, 4, 10).\n")


# --- UPDATED TERMINAL FIT LOGIC ---
def get_auto_terminal_dimensions(img):
    """
    Calculates the width/height to fit the image strictly within
    the current terminal view using the 'Downsize Factor n' approach.
    """
    # 1. Get Terminal Size
    term_w, term_h = shutil.get_terminal_size()

    # 2. Adjust for Rendering Logic (The "Double Width" Fix)
    # The renderer prints 2 characters for every 1 pixel (char + space/dot)
    # to correct aspect ratio. Therefore, our "logical max width" is
    # half the physical terminal width.
    # We subtract 2 extra columns for safety (avoid edge-case wrapping).
    max_w = (term_w // 2) - 2

    # We remove 1 line from height to leave room for the cursor/prompt at the bottom
    max_h = term_h - 1

    iw, ih = img.size

    # 3. Define Font Correction
    # This corrects vertical squash, but the horizontal spread is handled by max_w above.
    FONT_ASPECT_CORRECTION = 0.75

    # 4. Calculate "n" needed to fit Width
    # Formula: new_w = iw / n  =>  n = iw / new_w
    n_width = iw / max_w

    # 5. Calculate "n" needed to fit Height
    # Formula: new_h = (ih / n) * 0.5  =>  n = (ih * 0.5) / new_h
    n_height = (ih * FONT_ASPECT_CORRECTION) / max_h

    # 6. Determine Final 'n'
    # Use the larger n to satisfy the strictest constraint.
    n = max(n_width, n_height)

    # Sanity check: prevent div by zero
    if n == 0:
        n = 1

    # 7. Calculate Final Dimensions
    final_w = int(iw / n)
    final_h = int((ih / n) * FONT_ASPECT_CORRECTION)

    # Ensure at least 1x1
    final_w = max(1, final_w)
    final_h = max(1, final_h)

    return final_w, final_h
