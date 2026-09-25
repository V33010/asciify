from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ascii_art import cli


def test_parse_args_covers_core_flags(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "asciify",
            "-i",
            "image.png",
            "--color",
            "--width",
            "100",
            "--height",
            "50",
            "--aspect-ratio",
            "2",
            "--charset",
            "01",
            "--save",
            "--output-folder",
            "out",
            "--output-file-name",
            "result",
            "--html",
            "--full",
            "--no-preview",
            "--no-animate",
        ],
    )
    args = cli.parse_args()

    assert args.input_file == "image.png"
    assert args.color is True
    assert args.width == 100
    assert args.height == 50
    assert args.aspect_ratio == 2
    assert args.charset == "01"
    assert args.save is True
    assert args.output_folder == "out"
    assert args.output_file_name == "result"
    assert args.html is True
    assert args.full is True
    assert args.no_preview is True
    assert args.no_animate is True


def test_main_with_no_args_exits_cleanly(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["asciify"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "No arguments provided" in output
    assert "asciify -i <input_file>" in output


def test_main_routes_non_full_mode_to_terminal(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "argv", ["asciify", "-i", "image.png"])
    monkeypatch.setattr(cli.terminal, "run_terminal_pipeline", lambda args: calls.append(args))

    cli.main()
    assert len(calls) == 1
    assert calls[0].input_file == "image.png"


def test_main_routes_full_mode_to_legacy_loop(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "argv", ["asciify", "--full", "-i", "image.png"])
    monkeypatch.setattr(cli, "run_legacy_interactive_mode", lambda args: calls.append(args))
    answers = iter(["not-one"])
    monkeypatch.setattr("builtins.input", lambda: next(answers))

    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code is None
    assert len(calls) == 1


def test_legacy_mode_rejects_missing_input_file(monkeypatch):
    args = cli.parse_args() if False else None
    monkeypatch.setattr(sys, "argv", ["asciify", "--full", "-i", "/does/not/exist"])
    parsed = cli.parse_args()
    with pytest.raises(SystemExit) as exc:
        cli.run_legacy_interactive_mode(parsed)
    assert exc.value.code == 1


def test_legacy_mode_happy_path_runs_full_workflow(monkeypatch, tmp_path):
    image_path = tmp_path / "image.png"
    from PIL import Image
    Image.new("RGB", (4, 2)).save(image_path)
    args = cli.parse_args() if False else type("Args", (), {
        "no_animate": True,
        "input_file": str(image_path),
        "no_preview": True,
        "width": 2,
        "height": 1,
        "aspect_ratio": None,
        "charset": "01",
        "output_file_name": "out",
    })()
    calls = []
    monkeypatch.setattr(cli.ui, "print_header", lambda: None)
    monkeypatch.setattr(cli.image_loader, "load_image", lambda path, preview: Image.new("RGB", (4, 2)))
    monkeypatch.setattr(cli.image_resize, "resize_image", lambda img, w, h: img)
    monkeypatch.setattr(cli.converter, "image_to_ascii", lambda img, chars: [["0", "1"]])
    monkeypatch.setattr(cli.writer, "save_art", lambda *args, **kwargs: Path("out.txt"))
    monkeypatch.setattr(cli.ui, "clear_terminal", lambda: None)
    monkeypatch.setattr(cli.server, "start_server_and_open_browser", lambda path: calls.append(path))
    old_animate = cli.ui.CONFIG["animate"]
    try:
        cli.run_legacy_interactive_mode(args)
        assert calls == [Path("out.txt")]
        assert cli.ui.CONFIG["animate"] is False
    finally:
        cli.ui.CONFIG["animate"] = old_animate
