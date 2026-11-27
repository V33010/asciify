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


def test_play_video_should_reject_negative_downsize(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10), make_frame(20)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    video_renderer.play_video(
        "video.mp4", make_args(width=None, height=None, downsize=-2)
    )
    assert "positive number" in capsys.readouterr().out
    assert cap.released is True


def test_play_video_fill_rejects_charset(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)

    video_renderer.play_video("video.mp4", make_args(fill=True, charset="01"))
    assert "--charset/-c cannot be used with --fill or --fill-hd" in capsys.readouterr().out


def test_play_video_rejects_fill_and_fill_hd_together(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)

    video_renderer.play_video(
        "video.mp4", make_args(fill=True, fill_hd=True, charset=None)
    )
    assert "cannot be used together" in capsys.readouterr().out


def test_play_video_fill_uses_rust_fill_renderer(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10), make_frame(20)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer.ui, "clear_terminal", lambda: None)
    monkeypatch.setattr(video_renderer.ui, "move_cursor_home", lambda: None)
    monkeypatch.setattr(video_renderer.time, "sleep", lambda seconds: None)
    calls = []
    monkeypatch.setattr(
        video_renderer,
        "render_fill_to_string",
        lambda arr: calls.append(arr.copy()) or "FILLFRAME\n",
    )

    video_renderer.play_video("video.mp4", make_args(fill=True, charset=None))
    output = capsys.readouterr().out
    assert output.count("FILLFRAME") == 2
    assert len(calls) == 2
    assert calls[0].shape == (1, 2, 3)
    assert cap.released is True


def test_play_video_fill_hd_uses_rust_fill_hd_renderer(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10), make_frame(20)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer.ui, "clear_terminal", lambda: None)
    monkeypatch.setattr(video_renderer.ui, "move_cursor_home", lambda: None)
    monkeypatch.setattr(video_renderer.time, "sleep", lambda seconds: None)
    calls = []
    monkeypatch.setattr(
        video_renderer,
        "render_fill_hd_to_string",
        lambda arr: calls.append(arr.copy()) or "HDFILLFRAME\n",
    )

    video_renderer.play_video(
        "video.mp4", make_args(width=2, height=2, fill_hd=True, charset=None)
    )
    output = capsys.readouterr().out
    assert output.count("HDFILLFRAME") == 2
    assert len(calls) == 2
    assert calls[0].shape == (2, 2, 3)
    assert cap.released is True


def test_frame_prefetcher_delivers_all_frames_in_order():
    cap = FakeCapture([make_frame(10), make_frame(20), make_frame(30)])
    prefetcher = video_renderer._FramePrefetcher(cap, 2, 1, needs_rgb=False, maxsize=2).start()
    try:
        collected = []
        while True:
            frame = prefetcher.get()
            if frame is None:
                break
            collected.append(int(frame[0, 0, 0]))
    finally:
        prefetcher.stop()

    assert collected == [10, 20, 30]


def test_play_video_wraps_frames_in_sync_markers_and_restores_cursor(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10), make_frame(20)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer.ui, "clear_terminal", lambda: None)
    monkeypatch.setattr(video_renderer.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        video_renderer,
        "render_grayscale_to_string",
        lambda arr, chars: "FRAME\n",
    )

    video_renderer.play_video("video.mp4", make_args(color=False))
    output = capsys.readouterr().out

    assert video_renderer.ui.CURSOR_HIDE in output
    assert video_renderer.ui.CURSOR_SHOW in output
    assert output.count(video_renderer.ui.SYNC_START) == 2
    assert video_renderer.ui.SYNC_END in output


def test_play_video_uses_diff_renderer_and_skips_unchanged_frame_writes(monkeypatch, capsys):
    cap = FakeCapture([make_frame(10), make_frame(10), make_frame(200)])
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer.ui, "clear_terminal", lambda: None)
    monkeypatch.setattr(video_renderer.ui, "hide_cursor", lambda: None)
    monkeypatch.setattr(video_renderer.ui, "show_cursor", lambda: None)
    monkeypatch.setattr(video_renderer.time, "sleep", lambda seconds: None)

    resets = []
    responses = iter(["FULL_DIFF", "", "PARTIAL_DIFF"])
    monkeypatch.setattr(video_renderer, "reset_diff_state", lambda: resets.append(1))
    monkeypatch.setattr(
        video_renderer,
        "render_fill_hd_diff_to_string",
        lambda arr: next(responses),
    )

    video_renderer.play_video(
        "video.mp4", make_args(width=2, height=2, fill_hd=True, charset=None)
    )
    output = capsys.readouterr().out

    assert output == "FULL_DIFFPARTIAL_DIFF"
    assert len(resets) == 2  # reset before playback and in finally
    assert cap.released is True


def test_play_video_drops_stale_frames_when_falling_behind(monkeypatch, capsys):
    real_sleep = video_renderer.time.sleep
    frames = [make_frame(i * 40) for i in range(5)]
    cap = FakeCapture(frames, fps=10.0)  # frame_delay = 0.1s
    monkeypatch.setattr(video_renderer.cv2, "VideoCapture", lambda path: cap)
    monkeypatch.setattr(video_renderer.ui, "clear_terminal", lambda: None)
    monkeypatch.setattr(video_renderer.ui, "hide_cursor", lambda: None)
    monkeypatch.setattr(video_renderer.ui, "show_cursor", lambda: None)
    monkeypatch.setattr(video_renderer.time, "sleep", lambda seconds: None)

    # Simulate a large clock jump right after frame 0 so queued frames are stale.
    clock = iter([0.0, 0.35, 0.36, 0.37, 0.38, 0.39, 0.40])
    monkeypatch.setattr(video_renderer.time, "monotonic", lambda: next(clock, 0.5))

    rendered = []

    def fake_render(arr, chars):
        rendered.append(int(arr[0, 0, 0]))
        if len(rendered) == 1:
            real_sleep(0.02)
        return "X\n"

    monkeypatch.setattr(
        video_renderer,
        "render_grayscale_to_string",
        fake_render,
    )

    video_renderer.play_video("video.mp4", make_args(color=False))
    capsys.readouterr()

    assert len(rendered) >= 1
    assert len(rendered) < len(frames)
    assert cap.released is True
