# src/ascii_art/ui.py
import os
import sys
import time

CONFIG = {"animate": True}


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


def print_header():
    clear_terminal()
    cool_print("\n=== ASCII ART GENERATOR ===\n\n")


def get_ansi_colored_string(char, r, g, b):
    """
    Returns the character wrapped in TrueColor (24-bit) ANSI escape codes.
    Format: \033[38;2;R;G;Bm{char}\033[0m
    """
    return f"\033[38;2;{r};{g};{b}m{char}\033[0m"
