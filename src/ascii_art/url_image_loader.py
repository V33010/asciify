# src/ascii_art/url_image_loader.py
import os
import urllib.error
import urllib.request
from io import BytesIO
from urllib.parse import unquote, urlparse

# --- SECURITY CONFIG ---
MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024  # 10 MB Limit
TIMEOUT_SECONDS = 10
USER_AGENT = "Asciify-Term-CLI/1.0"

# Allowed MIME types and their fallback file extensions
MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/x-icon": ".ico",
}
ALLOWED_MIME_TYPES = set(MIME_TO_EXT)


def download_image(url):
    """
    Downloads image to memory with strict safety checks.
    Returns: (BytesIO object, filename_string) or (None, None)
    """
    print(f"Downloading from URL: {url} ...")

    # 1. Validate Scheme (Protocol)
    try:
        parsed_url = urlparse(url)
    except ValueError:
        print("❌ Error: Malformed URL.")
        return None, None

    if parsed_url.scheme not in ("http", "https"):
        print("❌ Error: URL must start with http:// or https://")
        return None, None

    try:
        # 2. Setup Request with User-Agent
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        # 3. Open Connection (Headers only first)
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:

            # --- SECURITY CHECK: Content-Length ---
            content_length = response.getheader("Content-Length")
            if content_length:
                try:
                    declared_size = int(content_length)
                except ValueError:
                    declared_size = None
                if declared_size is not None and declared_size > MAX_DOWNLOAD_SIZE:
                    print(
                        f"❌ Error: Image too large ({declared_size / 1024 / 1024:.2f} MB). Max is 10 MB."
                    )
                    return None, None

            # --- SECURITY CHECK: Content-Type ---
            # Verify the server actually claims this is an image
            mime_type = ""
            content_type = response.getheader("Content-Type")
            if content_type:
                # Clean up header (e.g., "image/png; charset=utf-8" -> "image/png")
                mime_type = content_type.split(";")[0].strip().lower()
                if mime_type not in ALLOWED_MIME_TYPES:
                    print(
                        f"❌ Error: Invalid Content-Type '{mime_type}'. Expected an image."
                    )
                    return None, None

            # 4. Stream Download (Prevent Memory Exhaustion)
            img_data = BytesIO()
            bytes_downloaded = 0
            chunk_size = 8192

            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                bytes_downloaded += len(chunk)
                if bytes_downloaded > MAX_DOWNLOAD_SIZE:
                    print("❌ Error: Download exceeded maximum size (10 MB).")
                    return None, None
                img_data.write(chunk)

            img_data.seek(0)

            # 5. Determine Filename (Robust Extraction)
            # Unquote handles %20 spaces and other encoding
            path_path = unquote(parsed_url.path)
            filename = os.path.basename(path_path)

            # Sanity check: If filename is empty or has no extension, fallback
            if not filename or "." not in filename:
                ext = MIME_TO_EXT.get(mime_type, ".jpg")
                filename = f"downloaded_image{ext}"

            return img_data, filename

    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        print(f"❌ Network Error: {e.reason}")
    except Exception as e:
        print(f"❌ Error processing URL: {e}")

    return None, None
