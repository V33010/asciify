# src/ascii_art/charset.py

DEFAULT_CHARSET = " .,:;'-|!)]>#$@%"
SIMPLE_CHARSET = " .:-=+*#%@"
BLOCKS_CHARSET = " ░▒▓█"
BLOCKS_EXTNEDED_CHARSET = " ░░▒▒▓▓██"
BINARY_CHARSET = "10"
CYBERPUNK_CHARSET = " .:?08NM"
BRAILLE_CHARSET = " ⠐⠠⢀⠂⠔⢄⠒⠤⢆⠖⠦⢖⠶⠷⡷⠿⣟⣯⣷⣾⣿"
BRAILLE_SMALL_CHARSET = "⠀⠁⠃⠇⠏⠟⠿⡿⣿"
TECH_SHADER_CHARSET = "⠂⠔⠦⠶⠷▏░⠿▎▍▒▓▌▟▋▊▉█"


def get_charset(custom_charset=None):
    """
    Returns the charset to use. Validates custom input.
    """
    if custom_charset:
        if isinstance(custom_charset, str) and len(custom_charset) > 0:
            return custom_charset
        else:
            raise ValueError("Custom charset must be a non-empty string.")
    # return DEFAULT_CHARSET
    # return BLOCKS_CHARSET
    # return BINARY_CHARSET
    # return CYBERPUNK_CHARSET
    return BLOCKS_EXTNEDED_CHARSET
    # return BRAILLE_CHARSET
    # return TECH_SHADER_CHARSET
    # return SIMPLE_CHARSET
    # return BRAILLE_SMALL_CHARSET
