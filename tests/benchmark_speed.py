#!/usr/bin/env python3
"""Clean, repeatable performance benchmark for Asciify.

Measures the real processing pipelines without terminal I/O or real-time video
sleeping. The report puts the total time first, followed by a compact stage
breakdown so speed regressions/improvements are obvious at a glance.

Typical usage:

    uv run python tests/benchmark_speed.py
    uv run python tests/benchmark_speed.py --runs 20 --warmups 3 --frames 120

Save a baseline before optimization:

    uv run python tests/benchmark_speed.py \
        --runs 20 --warmups 3 --frames 120 \
        --save-baseline benchmarks/baseline.json

Compare later work against that baseline:

    uv run python tests/benchmark_speed.py \
        --runs 20 --warmups 3 --frames 120 \
        --baseline benchmarks/baseline.json

Useful selectors:

    --image-only
    --video-only
    --grayscale-only
    --color-only
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ascii_art import converter, image_resize, ui, video_renderer  # noqa: E402
from ascii_art.charset import CHARSETS, get_charset  # noqa: E402


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

LINE = "=" * 72
THIN = "-" * 72


def ms(ns: int) -> float:
    return ns / 1_000_000.0


def format_ms(value: float) -> str:
    if value < 1:
        return f"{value:.3f} ms"
    if value < 100:
        return f"{value:.2f} ms"
    return f"{value:.1f} ms"


def format_percent(value: float) -> str:
    return f"{value:5.1f}%"


def format_delta(percent: float | None) -> str:
    if percent is None:
        return "n/a"
    if percent < 0:
        return f"{abs(percent):5.1f}% faster"
    if percent > 0:
        return f"{percent:5.1f}% slower"
    return "same"


def percentile(samples: list[float], p: float) -> float:
    """Linear-interpolated percentile; p is in [0, 100]."""
    if not samples:
        raise ValueError("percentile requires at least one sample")
    if len(samples) == 1:
        return samples[0]

    values = sorted(samples)
    rank = (len(values) - 1) * (p / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return values[low]
    weight = rank - low
    return values[low] * (1.0 - weight) + values[high] * weight


@dataclass
class Stats:
    samples_ms: list[float]

    @property
    def mean(self) -> float:
        return statistics.fmean(self.samples_ms)

    @property
    def median(self) -> float:
        return statistics.median(self.samples_ms)

    @property
    def minimum(self) -> float:
        return min(self.samples_ms)

    @property
    def maximum(self) -> float:
        return max(self.samples_ms)

    @property
    def stdev(self) -> float:
        if len(self.samples_ms) < 2:
            return 0.0
        return statistics.stdev(self.samples_ms)

    @property
    def p95(self) -> float:
        return percentile(self.samples_ms, 95)


@dataclass
class StageRun:
    """One complete benchmark run split into named stages."""

    stages_ms: dict[str, float]

    @property
    def total_ms(self) -> float:
        return sum(self.stages_ms.values())


@dataclass
class BenchmarkResult:
    name: str
    unit: str
    runs: list[StageRun]
    metadata: dict[str, object]

    @property
    def total(self) -> Stats:
        return Stats([run.total_ms for run in self.runs])

    def stage_stats(self, stage: str) -> Stats:
        return Stats([run.stages_ms[stage] for run in self.runs])

    @property
    def stage_names(self) -> list[str]:
        return list(self.runs[0].stages_ms)

    def bottleneck(self) -> tuple[str, float]:
        medians = {
            stage: self.stage_stats(stage).median
            for stage in self.stage_names
        }
        return max(medians.items(), key=lambda item: item[1])

    def to_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "unit": self.unit,
            "metadata": self.metadata,
            "total_median_ms": self.total.median,
            "total_mean_ms": self.total.mean,
            "stages_median_ms": {
                stage: self.stage_stats(stage).median
                for stage in self.stage_names
            },
        }


# ---------------------------------------------------------------------------
# Generic timing
# ---------------------------------------------------------------------------


def run_repeated(
    fn: Callable[[], StageRun],
    runs: int,
    warmups: int,
) -> list[StageRun]:
    for _ in range(warmups):
        fn()

    return [fn() for _ in range(runs)]


# ---------------------------------------------------------------------------
# Input discovery
# ---------------------------------------------------------------------------


def discover_image() -> Path | None:
    input_dir = ROOT / "assets" / "input"
    preferred_names = (
        "sample-image.jpg",
        "sample-image.jpeg",
        "sample-image.png",
        "sample.jpg",
        "sample.jpeg",
        "sample.png",
    )

    for name in preferred_names:
        path = input_dir / name
        if path.is_file():
            return path

    if not input_dir.is_dir():
        return None

    extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".webp",
        ".tif",
        ".tiff",
    }

    candidates = sorted(
        (
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() in extensions
        ),
        key=lambda path: path.name.lower(),
    )
    return candidates[0] if candidates else None


def discover_video() -> Path | None:
    path = ROOT / "assets" / "input" / "sample-video.mp4"
    return path if path.is_file() else None


def load_image(path: Path | None) -> tuple[Image.Image, str]:
    if path is not None:
        with Image.open(path) as image:
            return image.convert("RGB").copy(), str(path)

    # Deterministic fallback. Useful when running the benchmark before assets
    # have been added to the working tree.
    width, height = 1280, 720
    y, x = np.indices((height, width))
    array = np.empty((height, width, 3), dtype=np.uint8)
    array[..., 0] = (x * 255 // width).astype(np.uint8)
    array[..., 1] = (y * 255 // height).astype(np.uint8)
    array[..., 2] = ((x + y) * 255 // (width + height)).astype(np.uint8)
    return Image.fromarray(array, mode="RGB"), "generated deterministic fallback"


# ---------------------------------------------------------------------------
# Image benchmark
# ---------------------------------------------------------------------------


def format_grayscale_grid(ascii_grid: list[list[str]]) -> str:
    return "\n".join(
        "".join(char + " " for char in row)
        for row in ascii_grid
    ) + "\n"


def make_image_gray_run(
    image_path: Path | None,
    target_w: int,
    target_h: int,
    charset: str,
) -> StageRun:
    stages: dict[str, float] = {}

    start = time.perf_counter_ns()
    image, _ = load_image(image_path)
    stages["load image"] = ms(time.perf_counter_ns() - start)

    start = time.perf_counter_ns()
    resized = image_resize.resize_image(image, target_w, target_h)
    stages["resize"] = ms(time.perf_counter_ns() - start)

    start = time.perf_counter_ns()
    ascii_grid = converter.image_to_ascii(resized, charset)
    stages["ASCII conversion"] = ms(time.perf_counter_ns() - start)

    start = time.perf_counter_ns()
    format_grayscale_grid(ascii_grid)
    stages["format output"] = ms(time.perf_counter_ns() - start)

    return StageRun(stages)


def make_image_color_run(
    image_path: Path | None,
    target_w: int,
    target_h: int,
    charset: str,
) -> StageRun:
    if converter.render_frame_to_string is None:
        raise RuntimeError("Rust extension is required for the color benchmark")

    stages: dict[str, float] = {}

    start = time.perf_counter_ns()
    image, _ = load_image(image_path)
    stages["load image"] = ms(time.perf_counter_ns() - start)

    start = time.perf_counter_ns()
    resized = image_resize.resize_image(image, target_w, target_h)
    stages["resize"] = ms(time.perf_counter_ns() - start)

    start = time.perf_counter_ns()
    converter.render_image_to_string(resized, charset)
    stages["Rust ANSI rendering"] = ms(time.perf_counter_ns() - start)

    return StageRun(stages)


def run_image_benchmark(
    args: argparse.Namespace,
    image_path: Path | None,
    charset: str,
) -> list[BenchmarkResult]:
    image, source = load_image(image_path)
    target_w = args.width
    target_h = max(1, int(round(target_w * image.height / image.width)))

    results: list[BenchmarkResult] = []

    if args.mode in {"all", "grayscale"}:
        runs = run_repeated(
            lambda: make_image_gray_run(
                image_path,
                target_w,
                target_h,
                charset,
            ),
            args.runs,
            args.warmups,
        )
        results.append(
            BenchmarkResult(
                name="Image / grayscale",
                unit="image",
                runs=runs,
                metadata={
                    "source": source,
                    "input_size": f"{image.width}x{image.height}",
                    "output_size": f"{target_w}x{target_h}",
                    "charset_length": len(charset),
                    "mode": "grayscale",
                },
            )
        )

    if args.mode in {"all", "color"}:
        if converter.render_frame_to_string is not None:
            runs = run_repeated(
                lambda: make_image_color_run(
                    image_path,
                    target_w,
                    target_h,
                    charset,
                ),
                args.runs,
                args.warmups,
            )
            results.append(
                BenchmarkResult(
                    name="Image / color",
                    unit="image",
                    runs=runs,
                    metadata={
                        "source": source,
                        "input_size": f"{image.width}x{image.height}",
                        "output_size": f"{target_w}x{target_h}",
                        "charset_length": len(charset),
                        "mode": "color",
                        "renderer": "Rust direct ANSI string rendering",
                    },
                )
            )

    return results


# ---------------------------------------------------------------------------
# Video benchmark
# ---------------------------------------------------------------------------


def render_grayscale_frame(frame_rgb: np.ndarray, charset: str) -> str:
    image = Image.fromarray(frame_rgb)
    ascii_grid = converter.image_to_ascii(image, charset)
    return format_grayscale_grid(ascii_grid)


def render_color_frame(frame_rgb: np.ndarray, charset: str) -> str:
    if video_renderer.render_frame_to_string is None:
        raise RuntimeError("Rust extension is required for the color benchmark")
    return video_renderer.render_frame_to_string(frame_rgb, list(charset))


def make_video_run(
    video_path: Path,
    width: int,
    max_frames: int,
    charset: str,
    color: bool,
) -> StageRun:
    cap_open_start = time.perf_counter_ns()
    cap = cv2.VideoCapture(str(video_path))
    open_ms = ms(time.perf_counter_ns() - cap_open_start)

    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"could not open video: {video_path}")

    try:
        # BGR -> RGB is required only by the color renderer. The grayscale
        # converter is channel-order independent, so grayscale stays in the
        # OpenCV-native BGR layout and avoids that extra full-frame copy.
        if color:
            stages = {
                "open video": open_ms,
                "decode": 0.0,
                "resize": 0.0,
                "BGR -> RGB": 0.0,
                "render": 0.0,
            }
        else:
            stages = {
                "open video": open_ms,
                "decode": 0.0,
                "resize": 0.0,
                "render": 0.0,
            }

        frames = 0

        while frames < max_frames:
            start = time.perf_counter_ns()
            ret, frame = cap.read()
            stages["decode"] += ms(time.perf_counter_ns() - start)

            if not ret:
                break

            start = time.perf_counter_ns()
            height, source_width = frame.shape[:2]
            target_height = max(
                1,
                int(round(width * height / source_width)),
            )
            frame_resized = image_resize.resize_video_frame(
                frame,
                width,
                target_height,
            )
            stages["resize"] += ms(time.perf_counter_ns() - start)

            if color:
                start = time.perf_counter_ns()
                frame_rgb = cv2.cvtColor(
                    frame_resized,
                    cv2.COLOR_BGR2RGB,
                )
                stages["BGR -> RGB"] += ms(time.perf_counter_ns() - start)

                start = time.perf_counter_ns()
                render_color_frame(frame_rgb, charset)
                stages["render"] += ms(time.perf_counter_ns() - start)
            else:
                start = time.perf_counter_ns()
                render_grayscale_frame(frame_resized, charset)
                stages["render"] += ms(time.perf_counter_ns() - start)

            frames += 1

        stages["frames"] = frames  # metadata handled below, not a timing stage
        timing_stages = {
            key: value
            for key, value in stages.items()
            if key != "frames"
        }

        return StageRun(timing_stages)
    finally:
        cap.release()


def run_video_benchmark(
    args: argparse.Namespace,
    video_path: Path | None,
    charset: str,
) -> list[BenchmarkResult]:
    if video_path is None:
        return []

    results: list[BenchmarkResult] = []

    video_cap = cv2.VideoCapture(str(video_path))
    if not video_cap.isOpened():
        video_cap.release()
        raise RuntimeError(f"could not open video: {video_path}")

    source_width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    source_fps = float(video_cap.get(cv2.CAP_PROP_FPS))
    video_cap.release()

    modes: list[str]
    if args.mode == "all":
        modes = ["grayscale", "color"]
    else:
        modes = [args.mode]

    for mode in modes:
        color = mode == "color"

        if color and video_renderer.render_frame_to_string is None:
            continue

        runs = run_repeated(
            lambda: make_video_run(
                video_path,
                args.video_width,
                args.frames,
                charset,
                color,
            ),
            args.runs,
            args.warmups,
        )

        results.append(
            BenchmarkResult(
                name=f"Video / {mode}",
                unit="frame batch",
                runs=runs,
                metadata={
                    "source": str(video_path),
                    "source_size": f"{source_width}x{source_height}",
                    "source_fps": round(source_fps, 3) if source_fps > 0 else None,
                    "frames_requested_per_run": args.frames,
                    "render_width": args.video_width,
                    "resize_interpolation": "INTER_LINEAR",
                    "mode": mode,
                    "renderer": (
                        "Python/NumPy"
                        if not color
                        else "Rust string renderer"
                    ),
                },
            )
        )

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_result(result: BenchmarkResult, baseline: dict[str, object] | None) -> None:
    total = result.total
    slowest_stage, slowest_time = result.bottleneck()

    baseline_delta: float | None = None
    if baseline is not None:
        try:
            old_total = float(baseline["total_median_ms"])
            baseline_delta = ((total.median - old_total) / old_total) * 100
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            baseline_delta = None

    print()
    print(result.name.upper())
    print(THIN)

    metadata = result.metadata
    source = metadata.get("source", "unknown")
    output_size = metadata.get("output_size")
    render_width = metadata.get("render_width")
    requested_frames = metadata.get("frames_requested_per_run")

    if output_size is not None:
        print(
            f"Input: {source}   "
            f"{metadata.get('input_size', '?')} -> {output_size}"
        )
    else:
        print(f"Input: {source}   {metadata.get('source_size', '?')}")

    if render_width is not None:
        print(
            f"Render: width={render_width}, "
            f"up to {requested_frames} frames/run"
        )

    print()
    print(f"TOTAL MEDIAN        {format_ms(total.median)} / {result.unit}")
    print(f"TOTAL MEAN          {format_ms(total.mean)} / {result.unit}")
    print(f"BEST RUN            {format_ms(total.minimum)}")
    print(f"WORST RUN           {format_ms(total.maximum)}")
    print(f"P95 TOTAL           {format_ms(total.p95)}")

    if result.unit == "frame batch":
        frames_per_run = metadata.get("frames_requested_per_run")
        try:
            frames = int(frames_per_run)
        except (TypeError, ValueError):
            frames = 0

        if frames > 0:
            per_frame = total.median / frames
            fps = 1000.0 / per_frame if per_frame > 0 else 0.0
            print(f"PER FRAME           {format_ms(per_frame)}")
            print(f"THROUGHPUT          {fps:,.1f} FPS")

    if baseline_delta is not None:
        print(f"vs BASELINE         {format_delta(baseline_delta)}")

    print()
    print("BREAKDOWN            MEDIAN          SHARE")
    print(THIN)

    for stage in result.stage_names:
        stats = result.stage_stats(stage)
        share = (
            (stats.median / total.median) * 100
            if total.median > 0
            else 0.0
        )
        marker = "  <-- BOTTLENECK" if stage == slowest_stage else ""
        print(
            f"{stage:<20} "
            f"{format_ms(stats.median):>12}   "
            f"{format_percent(share):>6}{marker}"
        )

    print(THIN)
    print(
        f"Longest stage: {slowest_stage} "
        f"({format_ms(slowest_time)}, median)"
    )


def load_baseline(path: Path | None) -> dict[str, object]:
    if path is None:
        return {}

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    results = payload.get("results")
    if not isinstance(results, dict):
        raise ValueError(f"invalid baseline file: {path}")
    return results


def baseline_for(
    baselines: dict[str, object],
    result: BenchmarkResult,
) -> dict[str, object] | None:
    value = baselines.get(result.name)
    return value if isinstance(value, dict) else None


def save_baseline(
    path: Path,
    results: list[BenchmarkResult],
    args: argparse.Namespace,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "format_version": 1,
        "created_with": "asciify benchmark_speed.py",
        "config": {
            "runs": args.runs,
            "warmups": args.warmups,
            "width": args.width,
            "video_width": args.video_width,
            "frames": args.frames,
            "mode": args.mode,
            "charset": args.charset,
        },
        "results": {
            result.name: result.to_json()
            for result in results
        },
    }

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean, repeatable Asciify image/video performance benchmark."
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Measured runs per benchmark (default: 10).",
    )
    parser.add_argument(
        "--warmups",
        type=int,
        default=2,
        help="Warmup runs before measurement (default: 2).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=160,
        help="Image benchmark output width (default: 160).",
    )
    parser.add_argument(
        "--video-width",
        type=int,
        default=100,
        help="Video benchmark output width (default: 100).",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=60,
        help="Maximum video frames measured per run (default: 60).",
    )
    parser.add_argument(
        "--charset",
        default="default",
        help="Charset name supported by Asciify (default: default).",
    )
    parser.add_argument(
        "--mode",
        choices=("all", "grayscale", "color"),
        default="all",
        help="Benchmark grayscale, color, or both (default: all).",
    )
    parser.add_argument(
        "--image",
        type=Path,
        help="Explicit image path. Defaults to assets/input/sample-image.*.",
    )
    parser.add_argument(
        "--video",
        type=Path,
        help="Explicit video path. Defaults to assets/input/sample-video.mp4.",
    )
    parser.add_argument(
        "--image-only",
        action="store_true",
        help="Skip all video benchmarks.",
    )
    parser.add_argument(
        "--video-only",
        action="store_true",
        help="Skip all image benchmarks.",
    )
    parser.add_argument(
        "--grayscale-only",
        action="store_true",
        help="Alias for --mode grayscale.",
    )
    parser.add_argument(
        "--color-only",
        action="store_true",
        help="Alias for --mode color.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Compare median totals against a saved JSON baseline.",
    )
    parser.add_argument(
        "--save-baseline",
        type=Path,
        help="Save this run's median totals as a JSON baseline.",
    )

    args = parser.parse_args()

    aliases = int(args.grayscale_only) + int(args.color_only)
    if aliases > 1:
        parser.error("--grayscale-only and --color-only are mutually exclusive")

    if args.grayscale_only:
        args.mode = "grayscale"
    elif args.color_only:
        args.mode = "color"

    if args.image_only and args.video_only:
        parser.error("--image-only and --video-only are mutually exclusive")

    if args.runs <= 0:
        parser.error("--runs must be > 0")
    if args.warmups < 0:
        parser.error("--warmups must be >= 0")
    if args.width <= 0:
        parser.error("--width must be > 0")
    if args.video_width <= 0:
        parser.error("--video-width must be > 0")
    if args.frames <= 0:
        parser.error("--frames must be > 0")

    return args


def main() -> int:
    args = parse_args()

    image_path = args.image if args.image else discover_image()
    video_path = args.video if args.video else discover_video()

    try:
        charset = (
            CHARSETS["default"]
            if args.charset in (None, "default")
            else get_charset(args.charset)
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    rust_available = converter.render_frame_to_string is not None

    print()
    print(LINE)
    print("ASCIIFY SPEED BENCHMARK")
    print(LINE)
    print(
        f"Runs: {args.runs}   Warmups: {args.warmups}   "
        f"Image width: {args.width}   Video width: {args.video_width}   "
        f"Video frames/run: {args.frames}"
    )
    print(
        f"Mode: {args.mode}   Charset: {args.charset} "
        f"({len(charset)} chars)   Rust: "
        f"{'available' if rust_available else 'not built'}"
    )

    if image_path is None and not args.video_only:
        print(
            "\nIMAGE: no asset found; deterministic 1280x720 fallback will be used."
        )
    elif image_path is not None and not args.video_only:
        print(f"Image asset: {image_path}")

    if video_path is None and not args.image_only:
        print("Video: assets/input/sample-video.mp4 not found; video skipped.")
    elif video_path is not None and not args.image_only:
        print(f"Video asset: {video_path}")

    baselines: dict[str, object] = {}
    if args.baseline:
        try:
            baselines = load_baseline(args.baseline)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"\nError loading baseline '{args.baseline}': {exc}", file=sys.stderr)
            return 2

    results: list[BenchmarkResult] = []

    try:
        if not args.video_only:
            results.extend(run_image_benchmark(args, image_path, charset))

        if not args.image_only:
            results.extend(run_video_benchmark(args, video_path, charset))
    except RuntimeError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 2

    if not results:
        print("\nNo benchmarks were run.")
        return 1

    for result in results:
        print_result(result, baseline_for(baselines, result))

    if args.save_baseline:
        save_baseline(args.save_baseline, results, args)
        print()
        print(f"Baseline saved to: {args.save_baseline}")

    print()
    print(LINE)
    print("HOW TO READ THIS")
    print(LINE)
    print("TOTAL MEDIAN is the main number to track between optimizations.")
    print("Use the same machine, assets, dimensions, charset, and run count.")
    print("The bottleneck is the stage consuming the largest share of total time.")
    print("Grayscale video does not perform BGR -> RGB because its conversion is channel-order independent.")
    print("Color image output renders directly to one ANSI string in Rust; Python ANSI formatting is excluded.")
    print("Video total excludes terminal writes and real-time playback sleeping.")
    print(LINE)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
