from __future__ import annotations

import html
from pathlib import Path

import pytest

from ascii_art import writer


def test_clean_filename_removes_extension_and_unsafe_characters():
    assert writer.clean_filename("my image!.png") == "myimage"
    assert writer.clean_filename("a-b_c.txt") == "a-b_c"


def test_clean_filename_can_return_empty_string():
    assert writer.clean_filename("!!!.png") == ""


def test_generate_html_contains_document_structure_and_escaped_characters():
    grid = [["<", ">", "&"], [("@", (1, 2, 3))]]
    result = writer.generate_html(grid)

    assert result.startswith("<!DOCTYPE html>")
    assert "<html>" in result
    assert "</html>" in result
    assert html.escape("<") in result
    assert html.escape(">") in result
    assert html.escape("&") in result
    assert 'color: rgb(1,2,3)' in result
    assert ">@</span>" in result


def test_generate_html_handles_unicode_charset_characters():
    result = writer.generate_html([["░", "█"]])
    assert "░█" in result


def test_save_art_writes_text_output_with_space_after_each_character(tmp_path):
    grid = [["A", "B"], ["C", "D"]]
    output = writer.save_art(
        grid,
        original_filename=Path("picture.png"),
        output_folder=tmp_path,
        output_name="ascii_test",
    )

    assert output == tmp_path / "ascii_test.txt"
    assert output.read_text(encoding="utf-8") == "A B \nC D \n"


def test_save_art_writes_html_output(tmp_path):
    grid = [[("X", (10, 20, 30))]]
    output = writer.save_art(
        grid,
        original_filename=Path("picture.png"),
        output_folder=tmp_path,
        output_name="colored",
        as_html=True,
    )

    assert output == tmp_path / "colored.html"
    content = output.read_text(encoding="utf-8")
    assert "rgb(10,20,30)" in content


def test_save_art_creates_missing_output_directory(tmp_path):
    target = tmp_path / "nested" / "folder"
    output = writer.save_art(
        [["X"]],
        original_filename=Path("img.jpg"),
        output_folder=target,
        output_name="out",
    )
    assert output == target / "out.txt"
    assert output.exists()


def test_save_art_rejects_output_name_with_extension(tmp_path, capsys):
    output = writer.save_art(
        [["X"]],
        original_filename=Path("img.jpg"),
        output_folder=tmp_path,
        output_name="out.txt",
    )
    assert output is None
    assert "must NOT include an extension" in capsys.readouterr().out


def test_save_art_auto_names_from_original_filename(monkeypatch, tmp_path):
    class FixedDateTime:
        @classmethod
        def now(cls):
            from datetime import datetime

            return datetime(2026, 9, 25, 21, 0, 1)

    monkeypatch.setattr(writer, "datetime", FixedDateTime)
    output = writer.save_art(
        [["X"]],
        original_filename=Path("weird image!.png"),
        output_folder=tmp_path,
    )

    assert output == tmp_path / "ascii_weirdimage_25092026-210001.txt"
    assert output.exists()


def test_save_art_drops_color_metadata_for_plain_text(tmp_path):
    output = writer.save_art(
        [[("X", (1, 2, 3))]],
        original_filename=Path("img.png"),
        output_folder=tmp_path,
        output_name="plain",
        as_html=False,
    )
    assert output.read_text(encoding="utf-8") == "X \n"


def test_save_art_returns_none_when_output_directory_cannot_be_created(monkeypatch, tmp_path, capsys):
    target = tmp_path / "blocked"
    monkeypatch.setattr(writer.os, "makedirs", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("permission denied")))

    output = writer.save_art(
        [["X"]],
        original_filename=Path("img.png"),
        output_folder=target,
        output_name="out",
    )
    assert output is None
    assert "Error creating directory" in capsys.readouterr().out


def test_generate_html_escapes_tuple_character():
    result = writer.generate_html([[ ("<", (255, 0, 0)) ]])
    assert "&lt;" in result
    assert "<span style=\"color: rgb(255,0,0)\">" in result


def test_save_art_returns_none_on_write_error(monkeypatch, tmp_path, capsys):
    def broken_open(*args, **kwargs):
        raise OSError("write failed")

    monkeypatch.setattr(writer, "open", broken_open, raising=False)
    output = writer.save_art([["X"]], Path("img.png"), output_folder=tmp_path, output_name="out")
    assert output is None
    assert "Error saving file" in capsys.readouterr().out
