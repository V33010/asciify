#!/usr/bin/env python3

import re
import shlex
import subprocess
import sys
from pathlib import Path

# Updated to match your specific project structure
VERSION_FILE = Path("src/ascii_art/__version__.py")


def get_version():
    """Extract version string from __version__.py"""
    try:
        content = VERSION_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"❌ File not found: {VERSION_FILE}")
        print("   Did you run bump_version.py yet?")
        sys.exit(1)

    match = re.search(r'__version__\s*=\s*["\']([\d.]+)["\']', content)
    if not match:
        print(f"❌ Could not parse version from {VERSION_FILE}")
        sys.exit(1)

    return match.group(1)


def tag_exists(tag):
    """Check if a git tag already exists"""
    result = subprocess.run(
        ["git", "tag", "--list", tag], capture_output=True, text=True
    )
    return tag in result.stdout.strip().splitlines()


def run(command):
    """Run a command without invoking a shell."""
    args = shlex.split(command) if isinstance(command, str) else list(command)
    print(f"$ {' '.join(args)}")
    subprocess.run(args, shell=False, check=True)


def main():
    # 1. Get the current version from the code
    version = get_version()
    tag = f"v{version}"

    print(f"🔍 Detected version: {version}")

    # 2. Safety Check: Does this tag already exist?
    if tag_exists(tag):
        print(f"⚠️  Git tag '{tag}' already exists.")
        print(
            "   You might need to bump the version first using: python bump_version.py patch"
        )
        sys.exit(1)

    # 3. Confirmation
    confirm = input(f"🚀 Ready to tag and push release {tag}? (y/N): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("❌ Cancelled.")
        sys.exit(0)

    # 4. Execute
    try:
        run(f"git tag {tag}")
        run(f"git push origin {tag}")
        print(f"\n✅ Successfully tagged and pushed {tag}")
        print("   Go check your GitHub Actions tab!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error during git operations: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
