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
    # Fallback to 80x24 if detection fails
    # term_w, term_h = shutil.get_terminal_size((80, 24))
    term_w, term_h = shutil.get_terminal_size()

    # We remove 1 line from height to leave room for the cursor/prompt at the bottom
    # We keep width as-is, or remove 1 if your terminal auto-wraps aggressively
    max_w = term_w
    max_h = term_h - 1

    iw, ih = img.size

    # 2. Define Font Correction
    # Terminal characters are tall (~2x height of width).
    # To maintain visual aspect ratio, we must squash the height by ~0.5.
    FONT_ASPECT_CORRECTION = 0.75

    # 3. Calculate "n" needed to fit Width
    # Formula: new_w = iw / n  =>  n = iw / new_w
    # We want new_w <= max_w, so:
    n_width = iw / max_w

    # 4. Calculate "n" needed to fit Height
    # Formula: new_h = (ih / n) * 0.5  =>  n = (ih * 0.5) / new_h
    # We want new_h <= max_h, so:
    n_height = (ih * FONT_ASPECT_CORRECTION) / max_h

    # 5. Determine Final 'n'
    # To satisfy BOTH constraints (Width fit AND Height fit),
    # we must use the LARGER 'n' (which produces the smaller image).
    # This automatically handles the "Landscape vs Portrait" logic:
    # - If Portrait, ih is big, so n_height will likely be bigger -> Fits to Height.
    # - If Landscape, iw is big, so n_width will likely be bigger -> Fits to Width.
    # - If Landscape but super tall result (the "catch"), n_height becomes bigger -> Fits to Height.
    n = max(n_width, n_height)

    # Sanity check: prevent upscaling (n < 1) unless you want tiny images to fill screen.
    # For a viewer, usually we accept n < 1 (zoom in), but if you prefer strictly
    # "Fit inside but don't upscale", uncomment the next line:
    # n = max(n, 1.0)

    if n == 0:
        n = 1  # Prevent div by zero for weird edge cases

    # 6. Calculate Final Dimensions
    final_w = int(iw / n)
    final_h = int((ih / n) * FONT_ASPECT_CORRECTION)

    # Ensure at least 1x1
    final_w = max(1, final_w)
    final_h = max(1, final_h)

    return final_w, final_h
