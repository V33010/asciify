from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
from PIL import Image

from ascii_art import terminal


def make_args(**overrides):
    values = dict(
        show_charsets=False,
        set_charset=None,
        input_file=None,
        save=False,
        output_folder=None,
        output_file_name=None,
        html=False,
        color=False,
        width=None,
        height=None,
        aspect_ratio=None,
        downsize=None,
        charset=None,
    )
    values.update(overrides)
    return Namespace(**values)


def test_terminal_pipeline_rejects_missing_input(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        terminal.run_terminal_pipeline(make_args(input_file=None))
    assert exc.value.code == 1
    assert "Input file is required" in capsys.readouterr().out


def test_terminal_pipeline_rejects_nonexistent_local_file(tmp_path, capsys):
    path = tmp_path / "missing.png"
    with pytest.raises(SystemExit) as exc:
        terminal.run_terminal_pipeline(make_args(input_file=str(path)))
    assert exc.value.code == 1
    assert "not found" in capsys.readouterr().out


def test_terminal_pipeline_rejects_conflicting_aspect_ratio(tmp_path, capsys):
    image_path = tmp_path / "image.png"
    Image.new("RGB", (100, 50)).save(image_path)

    with pytest.raises(SystemExit) as exc:
        terminal.run_terminal_pipeline(
            make_args(input_file=str(image_path), width=100, height=100, aspect_ratio=2)
        )
    assert exc.value.code == 1
    assert "implies ratio" in capsys.readouterr().out


def test_terminal_pipeline_renders_grayscale_and_saves_text(tmp_path, capsys):
    image_path = tmp_path / "image.png"
    Image.new("RGB", (2, 1), (0, 255, 0)).save(image_path)

    terminal.run_terminal_pipeline(
        make_args(
            input_file=str(image_path),
            width=2,
            height=1,
            charset="01",
            save=True,
            output_folder=str(tmp_path),
            output_file_name="result",
        )
    )

    output = capsys.readouterr().out
    assert "1 1 " in output
    result = tmp_path / "result.txt"
    assert result.exists()
    assert result.read_text(encoding="utf-8") == "1 1 \n"


def test_terminal_pipeline_renders_color_directly_with_rust(monkeypatch, tmp_path, capsys):
    image_path = tmp_path / "image.png"
    Image.new("RGB", (1, 1), (1, 2, 3)).save(image_path)
    calls = {}

    def fake_render(img, chars):
        calls["rendered"] = (img.size, chars)
        return "\033[38;2;1;2;3mX.\033[0m\n"

    def unexpected_color_grid(*args, **kwargs):
        raise AssertionError("color terminal output should not build a Python color grid")

    monkeypatch.setattr(terminal.converter, "render_image_to_string", fake_render)
    monkeypatch.setattr(
        terminal.converter, "image_to_ascii_with_color", unexpected_color_grid
    )
    monkeypatch.setattr(
        terminal.ui, "get_ansi_colored_string", unexpected_color_grid
    )

    terminal.run_terminal_pipeline(
        make_args(
            input_file=str(image_path),
            width=1,
            height=1,
            charset="01",
            color=True,
        )
    )

    assert calls["rendered"] == ((1, 1), "01")
    assert capsys.readouterr().out == "\033[38;2;1;2;3mX.\033[0m\n"


def test_terminal_pipeline_color_reports_missing_rust_renderer(
    monkeypatch, tmp_path, capsys
):
    image_path = tmp_path / "image.png"
    Image.new("RGB", (1, 1), (1, 2, 3)).save(image_path)

    def missing_rust_renderer(*args, **kwargs):
        raise ImportError("Rust extension 'ascii_art_rs' not found")

    monkeypatch.setattr(terminal.converter, "render_image_to_string", missing_rust_renderer)

    with pytest.raises(SystemExit) as exc:
        terminal.run_terminal_pipeline(
            make_args(
                input_file=str(image_path),
                width=1,
                height=1,
                charset="01",
                color=True,
            )
        )

    assert exc.value.code == 1
    assert "Rust extension" in capsys.readouterr().out


def test_terminal_pipeline_color_still_builds_grid_when_saving(
    monkeypatch, tmp_path, capsys
):
    image_path = tmp_path / "image.png"
    Image.new("RGB", (1, 1), (1, 2, 3)).save(image_path)
    calls = {}

    monkeypatch.setattr(
        terminal.converter,
        "render_image_to_string",
        lambda img, chars: "RUST\n",
    )
    monkeypatch.setattr(
        terminal.converter,
        "image_to_ascii_with_color",
        lambda img, chars: [[("X", (1, 2, 3))]],
    )
    monkeypatch.setattr(
        terminal.writer,
        "save_art",
        lambda *args, **kwargs: calls.setdefault("saved", (args, kwargs))
        or Path("fake.txt"),
    )

    terminal.run_terminal_pipeline(
        make_args(
            input_file=str(image_path),
            width=1,
            height=1,
            charset="01",
            color=True,
            save=True,
            output_file_name="result",
        )
    )

    assert calls["saved"][0][0] == [[("X", (1, 2, 3))]]
    assert calls["saved"][1]["as_html"] is False
    assert capsys.readouterr().out == "RUST\n"


def test_terminal_pipeline_rejects_video_save_flags(monkeypatch, tmp_path, capsys):
    video = tmp_path / "sample.mp4"
    video.write_bytes(b"not a real video")

    with pytest.raises(SystemExit) as exc:
        terminal.run_terminal_pipeline(make_args(input_file=str(video), save=True))
    assert exc.value.code == 1
    assert "Saving output is not supported for video" in capsys.readouterr().out


def test_terminal_pipeline_routes_video_to_renderer(monkeypatch, tmp_path):
    video = tmp_path / "sample.mp4"
    video.write_bytes(b"placeholder")
    calls = []
    monkeypatch.setattr(
        terminal.video_renderer,
        "play_video",
        lambda path, args: calls.append((path, args)),
    )

    args = make_args(input_file=str(video))
    terminal.run_terminal_pipeline(args)

    assert calls == [(str(video), args)]


def test_terminal_pipeline_show_charsets_can_exit_without_input(capsys):
    terminal.run_terminal_pipeline(make_args(show_charsets=True))
    output = capsys.readouterr().out
    assert "Available Charsets" in output
    assert "default" in output


def test_terminal_set_charset_without_input_only_updates_config(monkeypatch):
    calls = []
    monkeypatch.setattr(
        terminal.charset_mod, "set_persistent_charset", lambda name: calls.append(name)
    )
    terminal.run_terminal_pipeline(make_args(set_charset="blocks"))
    assert calls == ["blocks"]


def test_terminal_invalid_set_charset_exits(monkeypatch, capsys):
    monkeypatch.setattr(
        terminal.charset_mod,
        "set_persistent_charset",
        lambda name: (_ for _ in ()).throw(ValueError("bad charset")),
    )
    with pytest.raises(SystemExit) as exc:
        terminal.run_terminal_pipeline(make_args(set_charset="bad"))
    assert exc.value.code == 1
    assert "bad charset" in capsys.readouterr().out


def test_terminal_downsize_path(tmp_path, capsys):
    image_path = tmp_path / "image.png"
    Image.new("RGB", (8, 4), (255, 255, 255)).save(image_path)
    terminal.run_terminal_pipeline(
        make_args(input_file=str(image_path), downsize=2, charset="01")
    )
    output = capsys.readouterr().out
    assert output.count("1 ") == 8
    assert output.count("\n") == 2


def test_terminal_invalid_downsize_exits(tmp_path, capsys):
    image_path = tmp_path / "image.png"
    Image.new("RGB", (8, 4)).save(image_path)
    with pytest.raises(SystemExit) as exc:
        terminal.run_terminal_pipeline(
            make_args(input_file=str(image_path), downsize=0)
        )
    assert exc.value.code == 1
    assert "positive number" in capsys.readouterr().out


def test_terminal_html_flag_is_forwarded_to_writer(monkeypatch, tmp_path):
    image_path = tmp_path / "image.png"
    Image.new("RGB", (1, 1)).save(image_path)
    calls = []
    monkeypatch.setattr(
        terminal.writer,
        "save_art",
        lambda *args, **kwargs: calls.append((args, kwargs)) or Path("out.html"),
    )
    terminal.run_terminal_pipeline(
        make_args(input_file=str(image_path), width=1, height=1, html=True)
    )
    assert calls[0][1]["as_html"] is True


def test_terminal_url_image_pipeline_uses_downloaded_filename(monkeypatch, capsys):
    img = Image.new("RGB", (1, 1), (255, 255, 255))
    img.info["custom_filename"] = "remote.png"
    monkeypatch.setattr(
        terminal.image_loader, "load_image", lambda url, preview=False: img
    )
    terminal.run_terminal_pipeline(
        make_args(
            input_file="https://example.com/remote.png", width=1, height=1, charset="01"
        )
    )
    assert "1 " in capsys.readouterr().out


def test_terminal_invalid_charset_exits(tmp_path, monkeypatch, capsys):
    image_path = tmp_path / "image.png"
    Image.new("RGB", (1, 1)).save(image_path)
    monkeypatch.setattr(
        terminal.charset_mod,
        "get_charset",
        lambda value: (_ for _ in ()).throw(ValueError("bad charset")),
    )
    with pytest.raises(SystemExit) as exc:
        terminal.run_terminal_pipeline(
            make_args(input_file=str(image_path), width=1, height=1)
        )
    assert exc.value.code == 1
    assert "bad charset" in capsys.readouterr().out
