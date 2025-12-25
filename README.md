# Asciify Term

![PyPI - Version](https://img.shields.io/pypi/v/asciify-term?style=flat-square&color=blue)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/asciify-term?style=flat-square)
![PyPI - License](https://img.shields.io/pypi/l/asciify-term?style=flat-square)
![PyPI - Downloads](https://img.shields.io/pypi/dm/asciify-term?style=flat-square)

**Asciify Term** is a modern, cross-platform CLI utility that renders high-resolution images as ASCII art directly in your terminal.

Originally built as a creative toy, it has evolved into a powerful **DevOps utility** for verifying image assets in headless environments (SSH, Docker, WSL) where GUI viewers are unavailable. It supports local files, remote URLs, and TrueColor rendering.

## 🚀 Features

- **Terminal-First Workflow:** Instantly render images to stdout with zero configuration.
- **Headless Support:** Perfect for verifying plot.png or asset files on remote servers via SSH.
- **URL Support:** Fetch and render images directly from the web (http://...) without manual downloading.
- **TrueColor Support:** Renders images in full 24-bit ANSI color.
- **Smart Resizing:** Automatically fits the output to your current terminal window dimensions.
- **Export Options:** Save outputs as plain text .txt or color-preserving .html.
- **Legacy Interactive Mode:** A guided menu system for creative exploration.

## Installation

Install directly from PyPI:

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

To view the image with its original colors (using ANSI escape codes):
```sh
asciify -i image.jpg --color
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

By default, asciify fits the image to your terminal. You can override this:

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


## Advanced: Interactive Mode

For a more guided, "creative" experience with animations and previews, use the --full flag. This launches the legacy interactive menu.

```sh 
asciify --full
```

## Configuration Reference

| Flag | Description |
| :--- | :--- |
| -i, --input-file | Path to local image OR URL (http://...). |
| --color | Enable TrueColor ANSI output. |
| -s, --save | Save output to current directory. |
| --output-folder | Specify folder for saved output. |
| --output-file-name | Specify filename (without extension). |
| --html | Save as .html file. |
| --width | Set target width. |
| --height | Set target height. |
| --aspect-ratio | Force specific aspect ratio. |
| --downsize | Downsize image by factor n. |
| -c, --charset | Use specific charset string. |
| --show-charsets | List all built-in charsets. |
| --set-charset | Set default charset preference. |
| --full | Launch legacy interactive mode. |

## License

Distributed under the MIT License. See LICENSE for more information.
