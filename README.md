# Asciify Term

![PyPI - Version](https://img.shields.io/pypi/v/asciify-term?style=flat-square&color=blue)
![Python](https://img.shields.io/badge/python-3.12+-blue?style=flat-square)
![Rust](https://img.shields.io/badge/built%20with-Rust-orange?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![PyPI - Downloads](https://img.shields.io/pypi/dm/asciify-term?style=flat-square)
![Latest GitHub Release](https://img.shields.io/github/v/release/V33010/asciify?style=flat-square&color=purple)
![Supported OS Platforms](https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-lightgrey?style=flat-square)
![GitHub Stars](https://img.shields.io/github/stars/V33010/asciify?style=flat-square)

**Asciify Term** is a modern, cross-platform CLI utility that renders high-resolution images and videos as ASCII art directly in your terminal.

Originally built as a creative toy, it has evolved into a powerful **DevOps utility** for verifying image assets in headless environments (SSH, Docker, WSL) where GUI viewers are unavailable. It supports local files, remote URLs, TrueColor rendering, and zero-whitespace solid pixel modes.

- **New in v0.6.0:** Added `--fill` (solid 24-bit background-colored cells) and `--fill-hd` (2× density `▀` half-block cells) with zero transparent area, plus a faster video pipeline with background decode/resize prefetching, deadline-based frame pacing, stateful Rust differential rendering, and tear-free DEC Mode 2026 synchronized output.
- **v0.5.0:** Rewrote the core rendering engine in Rust (`PyO3`), delivering high-speed frame rendering, memory efficiency, and smooth 30FPS+ video playback.

## 🚀 Features

- **Terminal-First Workflow:** Instantly render images to stdout with zero configuration.
- **Headless Support:** Perfect for verifying `plot.png` or asset files on remote servers via SSH.
- **URL Support:** Fetch and render images directly from the web (`http://...` / `https://...`) without manual downloading.
- **TrueColor Support:** Renders images and video in full 24-bit ANSI color.
- **Full-Fill & HD Modes:** Render solid 24-bit background-colored cells (`--fill`) or 2× density half-block cells (`--fill-hd`) with zero transparent area.
- **Smart Resizing:** Automatically fits the output to your current terminal window dimensions.
- **Export Options:** Save image outputs as plain text `.txt` or color-preserving `.html`.
- **Legacy Interactive Mode:** A guided menu system with browser preview for creative exploration.
- **Video Support:** Play MP4, MOV, AVI, MKV, WebM, FLV, and WMV files directly in your terminal (including remote video URLs).
- **Rust-Powered:** High-performance rendering engine with precomputed lookup tables, run-length ANSI deduplication, differential video updates, and low memory usage.

## Installation

Install directly from PyPI (recommended):

```sh
pip install asciify-term
```

## Usage

### 1. The Quick Scan (Default)

The primary use case is to quickly view an image in your terminal. The output automatically scales to fit your window.

```sh
# Local File
asciify -i image.jpg

# Remote URL
asciify -i https://example.com/logo.png
```

### 2. Color Mode

To view the image with its original colors (using 24-bit TrueColor ANSI escape codes):

```sh
asciify -i image.jpg --color
```

### 2b. Full-Fill & HD Modes (Zero Transparent Area)

Render solid 24-bit color blocks with no transparent character background. Both flags automatically imply `--color` and cannot be combined with `-c`/`--charset` or plain `.txt` saving (use `--html` to save).

```sh
# Solid 24-bit background-colored cells (regular resolution)
asciify -i image.jpg --fill

# High-density half-block (▀) mode (2x horizontal & 2x vertical resolution)
asciify -i image.jpg --fill-hd

# Video playback in HD full-fill mode
asciify -i my_video.mp4 --fill-hd

# Save full-fill output as zero-whitespace HTML
asciify -i image.jpg --fill-hd --html
```

### 3. Saving Output

You can save the generated art to a file instead of (or in addition to) printing it.

**Save to current directory (Auto-named):**

```sh
asciify -i image.jpg -s
# Creates: ascii_image_TIMESTAMP.txt
```

**Save with custom name/location:**

```sh
# Save as specific filename (no extension needed)
asciify -i image.jpg --output-file-name my_art

# Save to a specific folder
asciify -i image.jpg --output-folder ./art_gallery
```

**Save as HTML (Preserves Color):**

```sh
asciify -i image.jpg --color --html
```

### 4. Customizing Dimensions

By default, `asciify` fits the image to your terminal. You can override this:

```sh
# Force specific width (Height auto-calculated)
asciify -i image.jpg --width 100

# Force specific width AND aspect ratio
asciify -i image.jpg --width 100 --aspect-ratio 2.0

# Downsize by a factor of 4
asciify -i image.jpg --downsize 4
```

### 5. Managing Charsets

You can change the characters used for rendering (e.g., standard ASCII, blocks, braille).

**List available charsets:**

```sh
asciify --show-charsets
```

**Use a specific charset for one run:**

```sh
asciify -i image.jpg -c blocks
```

**Set a new default charset (Persistent):**

```sh
asciify --set-charset blocks
# All future runs will now use 'blocks' by default
```

### 6. Video Playback

```sh
# Play video in grayscale
asciify -i my_video.mp4

# Play video in TrueColor
asciify -i my_video.mp4 --color

# Play video in solid fill or HD half-block mode
asciify -i my_video.mp4 --fill
asciify -i my_video.mp4 --fill-hd
```

*Note: Saving output to file is disabled for video sources.*

## Advanced: Interactive Mode

For a more guided, "creative" experience with animations and browser previews, use the `--full` flag. This launches the legacy interactive menu.

```sh
asciify --full
```

## Configuration Reference

| Flag | Description |
| :--- | :--- |
| `-i`, `--input-file` | Path to local image/video OR URL (`http://...` / `https://...`). |
| `--color` | Enable TrueColor ANSI output. |
| `--fill` | Render solid 24-bit background-colored cells with zero transparent space (implies `--color`; incompatible with `-c`/`--charset`). |
| `--fill-hd` | Render high-density half-block (`▀`) 24-bit colored cells with 2× resolution and zero transparent space (implies `--color`; incompatible with `-c`/`--charset`). |
| `-s`, `--save` | Save output to current directory (images only). |
| `--output-folder` | Specify folder for saved output. |
| `--output-file-name` | Specify filename (without extension). |
| `--html` | Save as `.html` file (preserves color and supports `--fill`/`--fill-hd`). |
| `--width` | Set target width. |
| `--height` | Set target height. |
| `--aspect-ratio` | Force specific aspect ratio. |
| `--downsize` | Downsize image/video by factor `n`. |
| `-c`, `--charset` | Built-in charset name or custom character string. |
| `--show-charsets` | List all built-in charsets. |
| `--set-charset` | Set default charset preference. |
| `--full` | Launch legacy interactive mode. |
| `-V`, `--version` | Show installed version and exit. |

## License

Distributed under the MIT License. See `LICENSE` for more information.
