# Asciify

![Python Version](https://img.shields.io/badge/python-3.x-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Asciify** is a robust Command Line Interface (CLI) tool designed to convert images into ASCII art. It features a retro-style typewriter user interface, intelligent image resizing, and an integrated local web server for viewing results.

Built with modularity in mind, it runs seamlessly on Linux, Windows, and WSL2 environments.

## 🚀 Features

- **CLI Automation:** Full support for command-line arguments for batch processing or scripting.
- **Smart Resizing:** Maintains aspect ratio automatically or allows custom dimensions.
- **Visual Flair:** Optional "Cool Print" typewriter animation for terminal output.
- **Custom Charsets:** Use the built-in density map or provide your own characters.
- **Live Preview:** Instant browser preview of your generated art.
- **WSL Support:** Optimized for Linux and Windows Subsystem for Linux (WSL2).
- **Pure Python:** Built on top of Pillow and NumPy for efficiency.

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

1. Clone the repository:
```sh
git clone https://github.com/yourusername/asciify.git
cd asciify
```

2. Install dependencies (Pillow, NumPy):
```sh
pip install .
```

## Usage

You can use the tool in two ways: Interactive Mode or CLI Mode.

### 1. Interactive Mode

Simply run the module without arguments. The tool will guide you through selecting an image from the assets/input directory, resizing it, and saving it.

`python -m ascii_art`

### 2. Command Line Interface (CLI) Mode

For faster execution or scripts, pass arguments directly.

Example: Convert an image to 100 width, no preview, saved as 'my_art':
`python -m ascii_art -i path/to/image.jpg -w 100 -o my_art --no-preview`

Example: Use a custom character set:
`python -m ascii_art -i path/to/image.jpg -c "@#%*+=-:. "`

## Configuration Options

| Flag | Long Flag | Description |
| :--- | :--- | :--- |
| `-i` | `--input` | Path to the input image file. |
| `-o` | `--output` | Output filename (without extension). |
| `-w` | `--width` | Target width of the ASCII art. |
| `-h` | `--height` | Target height of the ASCII art. |
| `-c` | `--charset` | Custom string of characters to use for mapping. |
| | `--ratio` | Force a specific aspect ratio (float). |
| | `--no-preview` | Skip the image preview window. |
| | `--no-animate` | Disable the typewriter effect in the terminal. |
| | `--help` | Show the help message and exit. |

## Project Structure

```sh
asciify/
├── assets/
│   ├── input/       # Place source images here
│   └── output/      # Generated text files appear here
├── src/
│   └── ascii_art/   # Source code
├── tests/           # Unit tests
├── pyproject.toml   # Project configuration
└── README.md
```

## Contributing

1. Fork the project.
2. Create your feature branch (git checkout -b feature/AmazingFeature).
3. Commit your changes (git commit -m 'Add some AmazingFeature').
4. Push to the branch (git push origin feature/AmazingFeature).
5. Open a Pull Request.

## License

Distributed under the MIT License. See LICENSE for more information.
