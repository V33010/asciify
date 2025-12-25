# src/ascii_art/charset.py
import json
from pathlib import Path

# Define available charsets in a dictionary for easy lookup
CHARSETS = {
    "default": " .:;!|)]>#$@%",
    "simple": " .:-=+*#%@",
    "blocks": " ░▒▓█",
    "blocks_extended": " ░░▒▒▓▓██",
    "binary": "10",
    "cyberpunk": " .:?08NM",
    "braille": " ⠐⠠⢀⠂⠔⢄⠒⠤⢆⠖⠦⢖⠶⠷⡷⠿⣟⣯⣷⣾⣿",
    "braille_small": "⠀⠁⠃⠇⠏⠟⠿⡿⣿",
    "tech": " ⠂⠔⠦⠶⠷▏░⠿▎▍▒▓▌▟▋▊▉█",
}

CONFIG_FILE = Path.home() / ".asciify_config.json"


def get_charset(custom_charset=None):
    """
    Returns the charset to use.
    Priority:
    1. Custom string passed via CLI flag (-c)
    2. Persisted user preference (set via --set-charset)
    3. Default charset
    """
    # 1. Custom CLI Override
    if custom_charset:
        if isinstance(custom_charset, str) and len(custom_charset) > 0:
            return custom_charset
        else:
            raise ValueError("Custom charset must be a non-empty string.")

    # 2. Check Persistent Config
    saved_charset_name = load_persistent_charset_name()
    if saved_charset_name and saved_charset_name in CHARSETS:
        return CHARSETS[saved_charset_name]

    # 3. Default
    return CHARSETS["default"]


def set_persistent_charset(charset_name):
    """Saves the user's preferred charset name to a local config file."""
    if charset_name not in CHARSETS:
        available = ", ".join(CHARSETS.keys())
        raise ValueError(f"Invalid charset '{charset_name}'. Available: {available}")

    try:
        data = {"charset": charset_name}
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
        print(f"✅ Default charset set to: {charset_name}")
    except Exception as e:
        print(f"❌ Failed to save config: {e}")


def load_persistent_charset_name():
    """Loads the preferred charset name if it exists."""
    if not CONFIG_FILE.exists():
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("charset")
    except Exception:
        return None
