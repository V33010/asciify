import sys
from pathlib import Path

import toml


def read_current_version(pyproject_path: Path) -> str:
    data = toml.load(pyproject_path)
    return data["project"]["version"]


def write_new_version(pyproject_path: Path, version_file: Path, new_version: str):
    # 1. Update pyproject.toml
    data = toml.load(pyproject_path)
    data["project"]["version"] = new_version

    with open(pyproject_path, "w", encoding="utf-8") as f:
        toml.dump(data, f)

    print(f"✅ Updated pyproject.toml to version {new_version}")

    # 2. Update src/ascii_art/__version__.py
    # Ensure parent dir exists
    version_file.parent.mkdir(parents=True, exist_ok=True)

    # Write the Python version file
    version_file.write_text(f'__version__ = "{new_version}"\n', encoding="utf-8")
    print(f"✅ Updated {version_file} to version {new_version}")


def bump_patch(version: str) -> str:
    major, minor, patch = map(int, version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def bump_minor(version: str) -> str:
    major, minor, _ = map(int, version.split("."))
    return f"{major}.{minor + 1}.0"


def bump_major(version: str) -> str:
    major, _, _ = map(int, version.split("."))
    return f"{major + 1}.0.0"


def confirm_bump(old: str, new: str) -> bool:
    print(f"📦 Current version: {old}")
    print(f"🔁 Proposed version: {new}")
    response = input("Confirm version bump? (y/N): ").strip().lower()
    return response in ["y", "yes"]


def manual_mode(pyproject_path: Path, version_file: Path, current_version: str):
    print(f"📦 Current version: {current_version}")
    new_version = input("🔧 Enter new version: ").strip()
    if not new_version or new_version == current_version:
        print("⚠️  No change made. Exiting.")
        return
    write_new_version(pyproject_path, version_file, new_version)
    print(f"✅ Manual bump: {current_version} → {new_version}")


def main():
    pyproject_path = Path("pyproject.toml")
    # UPDATED PATH to match your project structure
    version_file = Path("src/ascii_art/__version__.py")

    if not pyproject_path.exists():
        print("❌ pyproject.toml not found.")
        return

    current_version = read_current_version(pyproject_path)

    if len(sys.argv) == 1:
        manual_mode(pyproject_path, version_file, current_version)
        return

    command = sys.argv[1].lower()

    if command == "patch":
        new_version = bump_patch(current_version)
        write_new_version(pyproject_path, version_file, new_version)
        print(f"✅ Patch bump: {current_version} → {new_version}")

    elif command == "minor":
        new_version = bump_minor(current_version)
        if confirm_bump(current_version, new_version):
            write_new_version(pyproject_path, version_file, new_version)
            print(f"✅ Minor bump: {current_version} → {new_version}")
        else:
            print("❌ Cancelled.")

    elif command == "major":
        new_version = bump_major(current_version)
        if confirm_bump(current_version, new_version):
            write_new_version(pyproject_path, version_file, new_version)
            print(f"✅ Major bump: {current_version} → {new_version}")
        else:
            print("❌ Cancelled.")

    else:
        print(f"❌ Unknown command: {command}")
        print("Usage: python bump_version.py [patch|minor|major]")


if __name__ == "__main__":
    main()
