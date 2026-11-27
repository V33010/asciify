import re
import sys
import tomllib
from pathlib import Path


def read_current_version(pyproject_path: Path) -> str:
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def _replace_section_version(
    content: str, section: str, new_version: str
) -> tuple[str, bool]:
    """Update `version = "..."` inside a specific TOML table while preserving formatting."""
    header_re = re.compile(rf"(?m)^\[{re.escape(section)}\]\s*$")
    header_match = header_re.search(content)
    if not header_match:
        return content, False

    start = header_match.end()
    next_header = re.search(r"(?m)^\[", content[start:])
    end = start + next_header.start() if next_header else len(content)
    section_body = content[start:end]

    version_re = re.compile(r'(?m)^(\s*version\s*=\s*["\'])([^"\']+)(["\'])')
    updated_body, count = version_re.subn(
        rf"\g<1>{new_version}\g<3>", section_body, count=1
    )
    if count == 0:
        return content, False
    return content[:start] + updated_body + content[end:], True


def write_new_version(
    pyproject_path: Path, cargo_path: Path, version_file: Path, new_version: str
):
    # 1. Update pyproject.toml
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    updated_pyproject, changed = _replace_section_version(
        pyproject_text, "project", new_version
    )
    if not changed:
        raise ValueError("Could not locate version field in [project] of pyproject.toml")
    pyproject_path.write_text(updated_pyproject, encoding="utf-8")
    print(f"✅ Updated pyproject.toml to version {new_version}")

    # 2. Update Cargo.toml
    if cargo_path.exists():
        cargo_text = cargo_path.read_text(encoding="utf-8")
        with cargo_path.open("rb") as f:
            cargo_data = tomllib.load(f)
        if "package" in cargo_data:
            updated_cargo, cargo_changed = _replace_section_version(
                cargo_text, "package", new_version
            )
            if cargo_changed:
                cargo_path.write_text(updated_cargo, encoding="utf-8")
                print(f"✅ Updated Cargo.toml to version {new_version}")
            else:
                print("⚠️  Warning: version field not found in [package] of Cargo.toml")
        else:
            print("⚠️  Warning: [package] section not found in Cargo.toml")
    else:
        print("⚠️  Warning: Cargo.toml not found")

    # 3. Update src/ascii_art/__version__.py
    version_file.parent.mkdir(parents=True, exist_ok=True)
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


def manual_mode(
    pyproject_path: Path, cargo_path: Path, version_file: Path, current_version: str
):
    print(f"📦 Current version: {current_version}")
    new_version = input("🔧 Enter new version: ").strip()
    if not new_version or new_version == current_version:
        print("⚠️  No change made. Exiting.")
        return
    write_new_version(pyproject_path, cargo_path, version_file, new_version)
    print(f"✅ Manual bump: {current_version} → {new_version}")


def main():
    pyproject_path = Path("pyproject.toml")
    cargo_path = Path("Cargo.toml")
    version_file = Path("src/ascii_art/__version__.py")

    if not pyproject_path.exists():
        print("❌ pyproject.toml not found.")
        return

    current_version = read_current_version(pyproject_path)

    if len(sys.argv) == 1:
        manual_mode(pyproject_path, cargo_path, version_file, current_version)
        return

    command = sys.argv[1].lower()

    if command == "patch":
        new_version = bump_patch(current_version)
        write_new_version(pyproject_path, cargo_path, version_file, new_version)
        print(f"✅ Patch bump: {current_version} → {new_version}")

    elif command == "minor":
        new_version = bump_minor(current_version)
        if confirm_bump(current_version, new_version):
            write_new_version(pyproject_path, cargo_path, version_file, new_version)
            print(f"✅ Minor bump: {current_version} → {new_version}")
        else:
            print("❌ Cancelled.")

    elif command == "major":
        new_version = bump_major(current_version)
        if confirm_bump(current_version, new_version):
            write_new_version(pyproject_path, cargo_path, version_file, new_version)
            print(f"✅ Major bump: {current_version} → {new_version}")
        else:
            print("❌ Cancelled.")

    else:
        print(f"❌ Unknown command: {command}")
        print("Usage: python bump_version.py [patch|minor|major]")


if __name__ == "__main__":
    main()
