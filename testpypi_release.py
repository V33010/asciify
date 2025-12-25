#!/usr/bin/env python3

import shutil
import subprocess
import sys
from pathlib import Path

# --- CONFIGURATION ---
# Set to False to upload to real PyPI
USE_TESTPYPI = False


def clean_build_artifacts():
    print("🧹 Cleaning previous builds...")
    directories = ["dist", "build"]
    directories.extend([str(p) for p in Path(".").glob("*.egg-info")])

    for folder in directories:
        path = Path(folder)
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            print(f"   - Removed {folder}")


def build_package():
    print("\n🔨 Building the project...")
    try:
        subprocess.run([sys.executable, "-m", "build"], check=True)
    except subprocess.CalledProcessError:
        print("❌ Build failed.")
        sys.exit(1)


def upload_package():
    dist_files = [str(f) for f in Path("dist").glob("*")]
    if not dist_files:
        print("❌ No files found in dist/.")
        sys.exit(1)

    command = ["twine", "upload"]

    # This tells twine to look for [testpypi] in your .pypirc file
    if USE_TESTPYPI:
        print("\n🚀 Uploading to TestPyPI...")
        command.extend(["--repository", "testpypi"])
    else:
        print("\n🚀 Uploading to REAL PyPI...")
        # Defaults to [pypi] in .pypirc

    command.extend(dist_files)

    try:
        subprocess.run(command, check=True)
        print("\n✅ Upload successful!")
    except subprocess.CalledProcessError:
        print("\n❌ Upload failed.")
        sys.exit(1)


def main():
    clean_build_artifacts()
    build_package()
    upload_package()


if __name__ == "__main__":
    main()
