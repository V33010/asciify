# src/ascii_art/url_image_loader.py
import os
import urllib.error
import urllib.request
from io import BytesIO
from urllib.parse import urlparse

# --- SECURITY CONFIG ---
MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024  # 10 MB Limit
TIMEOUT_SECONDS = 10
USER_AGENT = "Asciify-Term-CLI/1.0"


def download_image(url):
    """
    Downloads image to memory with safety checks.
    Returns: (BytesIO object, filename_string) or (None, None)
    """
    print(f"Downloading from URL: {url} ...")

    # 1. Validate Protocol
    if not (url.startswith("http://") or url.startswith("https://")):
        print("❌ Error: URL must start with http:// or https://")
        return None, None

    try:
        # 2. Setup Request with User-Agent
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        # 3. Open Stream with Timeout
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            # Check size header first (if available)
            content_length = response.getheader("Content-Length")
            if content_length and int(content_length) > MAX_DOWNLOAD_SIZE:
                print(
                    f"❌ Error: Image too large ({int(content_length) / 1024 / 1024:.2f} MB). Max is 10 MB."
                )
                return None, None

            # 4. Stream Download to limit memory usage
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

            # 5. Determine Filename
            # Try to get from URL path
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)

            # Fallback if URL ends in a query string or is weird
            if not filename or "." not in filename:
                filename = "downloaded_image.jpg"

            return img_data, filename

    except urllib.error.URLError as e:
        print(f"❌ Network Error: {e.reason}")
    except Exception as e:
        print(f"❌ Error processing URL: {e}")

    return None, None
