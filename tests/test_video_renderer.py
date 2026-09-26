from __future__ import annotations

from argparse import Namespace

import numpy as np
import pytest

from ascii_art import video_renderer


def make_args(**overrides):
    values = dict(
        width=2,
        height=1,
        aspect_ratio=None,
        downsize=None,
        charset="01",
        color=False,
    )
    values.update(overrides)
    return Namespace(**values)


class FakeCapture:
    def __init__(self, frames, fps=10.0, opened=True):
        self.frames = list(frames)
        self.fps = fps
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def get(self, prop):
        return self.fps

    def read(self):
        if self.frames:
            return True, self.frames.pop(0).copy()
        return False, None

    def release(self):
        self.released = True


def make_frame(value):
    return np.full((2, 4, 3), value, dtype=np.uint8)


def test_play_video_reports_unopenable_video(monkeypatch, capsys):
    cap = FakeCapture([], opened=False)
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)

    video_renderer.play_video("missing.mp4", make_args())
    assert "Could not open video file" in capsys.readouterr().out
    assert cap.released is False


def test_play_video_reports_empty_video(monkeypatch, capsys):
    cap = FakeCapture([], opened=True)
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)

    video_renderer.play_video("empty.mp4", make_args())
    output = capsys.readouterr().out
    assert "Video is empty" in output
    assert cap.released is True


def test_play_video_grayscale_processes_frames_and_releases(monkeypatch, capsys):
    frames = [make_frame(0), make_frame(255), make_frame(128)]
    cap = FakeCapture(frames, fps=30.0)
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer.ui, "clear_terminal", lambda: None)
    monkeypatch.setattr(video_renderer.ui, "move_cursor_home", lambda: None)
    monkeypatch.setattr(video_renderer.time, "sleep", lambda seconds: None)

    video_renderer.play_video("video.mp4", make_args())
    output = capsys.readouterr().out

    assert " " in output
    assert "1 1" in output
    assert cap.released is True


def test_play_video_uses_fallback_fps_when_video_reports_zero(monkeypatch):
    frames = [make_frame(10), make_frame(20)]
    cap = FakeCapture(frames, fps=0.0)
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer.ui, "clear_terminal", lambda: None)
    monkeypatch.setattr(video_renderer.ui, "move_cursor_home", lambda: None)
    sleep_calls = []
    monkeypatch.setattr(
        video_renderer.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

    video_renderer.play_video("video.mp4", make_args())
    assert cap.released is True
    assert sleep_calls  # proves the 30 FPS fallback path was reached


def test_play_video_rejects_bad_aspect_ratio(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)

    video_renderer.play_video(
        "video.mp4",
        make_args(width=2, height=1, aspect_ratio=3.0),
    )
    assert "Conflict" in capsys.readouterr().out


def test_play_video_rejects_invalid_downsize(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)

    video_renderer.play_video(
        "video.mp4", make_args(width=None, height=None, downsize="bad")
    )
    assert "positive number" in capsys.readouterr().out


def test_play_video_color_requires_rust(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer, "render_frame_to_string", None)

    video_renderer.play_video("video.mp4", make_args(color=True))
    assert "Rust extension not found" in capsys.readouterr().out


def test_play_video_color_uses_rust_renderer_when_available(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10), make_frame(20)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer.ui, "clear_terminal", lambda: None)
    monkeypatch.setattr(video_renderer.ui, "move_cursor_home", lambda: None)
    monkeypatch.setattr(video_renderer.time, "sleep", lambda seconds: None)
    calls = []
    monkeypatch.setattr(
        video_renderer,
        "render_frame_to_string",
        lambda arr, charset: calls.append((arr.copy(), charset)) or "RUST\n",
    )

    video_renderer.play_video("video.mp4", make_args(color=True))
    output = capsys.readouterr().out
    assert "RUST" in output
    assert len(calls) == 2
    assert calls[0][0].shape == (1, 2, 3)
    assert calls[0][1] == ["0", "1"]
    assert cap.released is True


def test_play_video_grayscale_uses_rust_renderer_when_available(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10), make_frame(20)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer.ui, "clear_terminal", lambda: None)
    monkeypatch.setattr(video_renderer.ui, "move_cursor_home", lambda: None)
    monkeypatch.setattr(video_renderer.time, "sleep", lambda seconds: None)

    calls = []
    monkeypatch.setattr(
        video_renderer,
        "render_grayscale_to_string",
        lambda arr, charset: calls.append((arr.copy(), charset)) or "RUSTGRAY\n",
    )

    def unexpected_python_conversion(*args, **kwargs):
        raise AssertionError("grayscale video should use the Rust renderer when available")

    monkeypatch.setattr(
        "ascii_art.converter.image_to_ascii",
        unexpected_python_conversion,
    )

    video_renderer.play_video("video.mp4", make_args(color=False))
    output = capsys.readouterr().out

    assert output.count("RUSTGRAY") == 2
    assert len(calls) == 2
    assert calls[0][0].shape == (1, 2, 3)
    assert calls[0][1] == ["0", "1"]
    assert cap.released is True


def test_play_video_grayscale_skips_bgr_to_rgb_conversion(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10), make_frame(20)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer.ui, "clear_terminal", lambda: None)
    monkeypatch.setattr(video_renderer.ui, "move_cursor_home", lambda: None)
    monkeypatch.setattr(video_renderer.time, "sleep", lambda seconds: None)

    def unexpected_color_conversion(*args, **kwargs):
        raise AssertionError("grayscale video should not convert BGR to RGB")

    monkeypatch.setattr(
        video_renderer.cv2,
        "cvtColor",
        unexpected_color_conversion,
    )

    video_renderer.play_video("video.mp4", make_args(color=False))

    capsys.readouterr()
    assert cap.released is True


def test_play_video_handles_keyboard_interrupt(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10), make_frame(20)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer.ui, "clear_terminal", lambda: print("CLEAR"))
    monkeypatch.setattr(video_renderer.ui, "move_cursor_home", lambda: None)
    monkeypatch.setattr(
        video_renderer,
        "render_grayscale_to_string",
        lambda *args: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    video_renderer.play_video("video.mp4", make_args())
    output = capsys.readouterr().out
    assert "Stopped." in output
    assert cap.released is True


def test_play_video_should_render_first_decoded_frame(monkeypatch):
    cap = FakeCapture([make_frame(10), make_frame(20), make_frame(30)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer.ui, "clear_terminal", lambda: None)
    monkeypatch.setattr(video_renderer.ui, "move_cursor_home", lambda: None)
    monkeypatch.setattr(video_renderer.time, "sleep", lambda seconds: None)

    seen = []
    monkeypatch.setattr(
        video_renderer,
        "render_grayscale_to_string",
        lambda frame, chars: seen.append(frame.copy()) or "0 \n",
    )

    video_renderer.play_video("video.mp4", make_args())
    assert len(seen) == 3


def test_play_video_should_release_capture_on_empty_video(monkeypatch):
    cap = FakeCapture([], opened=True)
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)

    video_renderer.play_video("empty.mp4", make_args())
    assert cap.released is True


def test_play_video_should_reject_negative_downsize(monkeypatch):
    cap = FakeCapture([make_frame(10), make_frame(20)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    video_renderer.play_video(
        "video.mp4", make_args(width=None, height=None, downsize=-2)
    )
