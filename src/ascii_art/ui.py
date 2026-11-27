# src/ascii_art/ui.py
import os
import time

CONFIG = {"animate": True}

# DEC Mode 2026 synchronized output + cursor control sequences
SYNC_START = "\033[?2026h"
SYNC_END = "\033[?2026l"
CURSOR_HOME = "\033[H"
CURSOR_HIDE = "\033[?25l"
CURSOR_SHOW = "\033[?25h"


def cool_print(string):
    if CONFIG["animate"]:
        for char in string:
            print(char, end="", flush=True)
            time.sleep(0.01)
    else:
        print(string, end="", flush=True)


def clear_terminal():
    """
    Hard clear: Wipes the screen completely (Windows/Linux standard).
    """
    os.system("cls" if os.name == "nt" else "clear")


def soft_clear():
    """
    Soft clear: Moves cursor to top-left and clears everything below it.
    This preserves the scrollback history so users can scroll up.
    """
    print("\033[H\033[J", end="")


def move_cursor_home():
    """
    Moves cursor to (0,0) without clearing the screen.
    Used for video rendering to overwrite the previous frame.
    """
    print(CURSOR_HOME, end="")


def hide_cursor():
    """Hides the terminal cursor during video playback to prevent flicker."""
    print(CURSOR_HIDE, end="", flush=True)


def show_cursor():
    """Restores the terminal cursor and ends any active synchronized update."""
    print(f"{SYNC_END}{CURSOR_SHOW}", end="", flush=True)


def print_header():
    clear_terminal()
    cool_print("\n=== ASCII ART GENERATOR ===\n\n")


def get_ansi_colored_string(char, r, g, b):
    r"""
    Returns the character wrapped in TrueColor (24-bit) ANSI escape codes.
    Format: \033[38;2;R;G;Bm{char}\033[0m
    """
    return f"\033[38;2;{r};{g};{b}m{char}\033[0m"
