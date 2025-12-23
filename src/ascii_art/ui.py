# src/ascii_art/ui.py
import os
import sys
import time

# Global configuration for animation
CONFIG = {"animate": True}


def cool_print(string):
    """
    Prints string with a typewriter effect if animation is enabled.
    """
    if CONFIG["animate"]:
        for char in string:
            print(char, end="", flush=True)
            time.sleep(0.01)  # Slightly faster than old code for better UX
    else:
        print(string, end="", flush=True)


def clear_terminal():
    """
    Clears the terminal screen.
    """
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    clear_terminal()
    cool_print("\n=== ASCII ART GENERATOR ===\n\n")
