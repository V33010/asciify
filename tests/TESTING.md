# Asciify test suite

The suite is designed to run from a source checkout and does not require the Rust extension for the Python-only tests.

## Install test dependencies

From the repository root:

```bash
uv pip install pytest coverage
```

`bump_version.py` imports the third-party `toml` package, but the current `pyproject.toml` does not declare it. To exercise the release-version tests as well, install it too:

```bash
uv pip install toml
```

## Run everything

```bash
pytest -q
```

See the reasons for skips and expected failures with:

```bash
pytest -q -rxXs
```

Run a single area:

```bash
pytest -q tests/test_converter.py
pytest -q tests/test_video_renderer.py
pytest -q tests/test_rust_renderer.py
```

## Rust tests

Build the PyO3 extension in development mode first:

```bash
uv run maturin develop --release
```

Then verify the Rust test file:

```bash
pytest -q tests/test_rust_renderer.py
```

The current test environment used to develop this suite did not have a Rust compiler, so these tests were intentionally configured to skip instead of silently testing a Python substitute.

## Image/video integration

`tests/test_integration_asset.py` looks for a supported image in `assets/input/` and runs a real load -> dimension calculation -> resize -> ASCII conversion path. If no image exists, it skips cleanly.

The speed benchmark automatically finds a supported image in `assets/input/`. It prefers `sample-image.png`, `sample-image.jpg`, `sample.png`, and `sample.jpg`, then falls back to the first supported image. If no image exists, it uses a deterministic generated image so the benchmark remains runnable.

For video, place the file at:

```text
assets/input/sample-video.mp4
```

or pass an explicit path with `--video`.

## Performance benchmark

Normal benchmark:

```bash
python tests/benchmark_speed.py
```

More stable comparison:

```bash
python tests/benchmark_speed.py --runs 20 --warmups 3 --frames 60
```

Image only:

```bash
python tests/benchmark_speed.py --image-only --runs 20 --warmups 3
```

Video only:

```bash
python tests/benchmark_speed.py --video-only --runs 10 --warmups 2 --frames 60
```

Color video/Rust path:

```bash
python tests/benchmark_speed.py --video-only --color-only --runs 10 --warmups 2 --frames 60
```

The color image benchmark now uses the production direct-Rust ANSI renderer, so it no longer measures Python per-character ANSI formatting. Color video already uses the same direct-Rust string renderer. The benchmark deliberately excludes terminal writes and real-time `sleep()` from the processing timing, because those would dominate the numbers and make optimization comparisons misleading. It separately measures image loading, resize, ASCII conversion/rendering, video decoding, BGR-to-RGB conversion where required, and per-frame throughput, and reports the longest median stage.
