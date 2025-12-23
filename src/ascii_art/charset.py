# src/ascii_art/charset.py

DEFAULT_CHARSET = " .,:;'`-_^/\\|!()[]<>#$@%"


def get_charset(custom_charset=None):
    """
    Returns the charset to use. Validates custom input.
    """
    if custom_charset:
        if isinstance(custom_charset, str) and len(custom_charset) > 0:
            return custom_charset
        else:
            raise ValueError("Custom charset must be a non-empty string.")
    return DEFAULT_CHARSET
