from __future__ import annotations

from ascii_art import ui


def test_get_ansi_colored_string_uses_truecolor_sequence():
    assert ui.get_ansi_colored_string("X", 1, 2, 3) == "\033[38;2;1;2;3mX\033[0m"


def test_get_ansi_colored_string_supports_multicharacter_text():
    result = ui.get_ansi_colored_string("AB", 255, 128, 0)
    assert result.startswith("\033[38;2;255;128;0m")
    assert result.endswith("\033[0m")
    assert "AB" in result


def test_cool_print_without_animation(monkeypatch, capsys):
    old = ui.CONFIG["animate"]
    ui.CONFIG["animate"] = False
    try:
        ui.cool_print("hello\n")
    finally:
        ui.CONFIG["animate"] = old
    assert capsys.readouterr().out == "hello\n"


def test_cool_print_with_animation_prints_all_characters(monkeypatch, capsys):
    old = ui.CONFIG["animate"]
    ui.CONFIG["animate"] = True
    monkeypatch.setattr(ui.time, "sleep", lambda _: None)
    try:
        ui.cool_print("abc")
    finally:
        ui.CONFIG["animate"] = old
    assert capsys.readouterr().out == "abc"


def test_soft_clear_emits_expected_ansi_sequence(capsys):
    ui.soft_clear()
    assert capsys.readouterr().out == "\033[H\033[J"


def test_move_cursor_home_emits_expected_ansi_sequence(capsys):
    ui.move_cursor_home()
    assert capsys.readouterr().out == "\033[H"


def test_clear_terminal_uses_platform_specific_command(monkeypatch):
    commands = []
    monkeypatch.setattr(ui.os, "system", lambda command: commands.append(command) or 0)
    monkeypatch.setattr(ui.os, "name", "posix")
    ui.clear_terminal()
    assert commands == ["clear"]


def test_print_header_clears_and_prints_banner(monkeypatch, capsys):
    monkeypatch.setattr(ui, "clear_terminal", lambda: print("CLEARED"))
    old = ui.CONFIG["animate"]
    ui.CONFIG["animate"] = False
    try:
        ui.print_header()
    finally:
        ui.CONFIG["animate"] = old
    output = capsys.readouterr().out
    assert "CLEARED" in output
    assert "ASCII ART GENERATOR" in output
