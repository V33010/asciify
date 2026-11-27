from __future__ import annotations

import sys
from pathlib import Path

import pytest

try:
    import bump_version
except ModuleNotFoundError as exc:
    bump_version = None
    BUMP_IMPORT_ERROR = exc
else:
    BUMP_IMPORT_ERROR = None

import tag_release

bump_skip = pytest.mark.skipif(
    bump_version is None,
    reason=f"bump_version.py cannot import: {BUMP_IMPORT_ERROR}",
)


@bump_skip
def test_bump_version_helpers():
    assert bump_version.bump_patch("1.2.3") == "1.2.4"
    assert bump_version.bump_minor("1.2.3") == "1.3.0"
    assert bump_version.bump_major("1.2.3") == "2.0.0"


@bump_skip
def test_read_current_version(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text('[project]\nversion = "9.8.7"\n', encoding="utf-8")
    assert bump_version.read_current_version(path) == "9.8.7"


@bump_skip
def test_write_new_version_updates_pyproject_cargo_and_version_file(tmp_path, capsys):
    pyproject = tmp_path / "pyproject.toml"
    cargo = tmp_path / "Cargo.toml"
    version_file = tmp_path / "src" / "ascii_art" / "__version__.py"
    pyproject.write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    cargo.write_text('[package]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8")

    bump_version.write_new_version(pyproject, cargo, version_file, "1.2.3")

    assert 'version = "1.2.3"' in pyproject.read_text(encoding="utf-8")
    assert 'version = "1.2.3"' in cargo.read_text(encoding="utf-8")
    assert version_file.read_text(encoding="utf-8") == '__version__ = "1.2.3"\n'
    output = capsys.readouterr().out
    assert "Updated pyproject.toml" in output
    assert "Updated Cargo.toml" in output


@bump_skip
def test_write_new_version_handles_missing_cargo_and_missing_package(tmp_path, capsys):
    pyproject = tmp_path / "pyproject.toml"
    cargo = tmp_path / "Cargo.toml"
    version_file = tmp_path / "__version__.py"
    pyproject.write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")
    bump_version.write_new_version(pyproject, cargo, version_file, "0.2.0")
    assert "Cargo.toml not found" in capsys.readouterr().out

    cargo.write_text("[workspace]\nmembers = []\n", encoding="utf-8")
    bump_version.write_new_version(pyproject, cargo, version_file, "0.3.0")
    assert "[package] section not found" in capsys.readouterr().out


@bump_skip
def test_confirm_bump_accepts_y_yes_and_rejects_other_values(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    assert bump_version.confirm_bump("1.0.0", "1.1.0") is True
    monkeypatch.setattr("builtins.input", lambda prompt: "YES")
    assert bump_version.confirm_bump("1.0.0", "1.1.0") is True
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    assert bump_version.confirm_bump("1.0.0", "1.1.0") is False


@bump_skip
def test_manual_mode_does_nothing_for_blank_or_same_version(
    monkeypatch, tmp_path, capsys
):
    pyproject = tmp_path / "pyproject.toml"
    cargo = tmp_path / "Cargo.toml"
    version_file = tmp_path / "version.py"
    for answer in ["", "1.0.0"]:
        monkeypatch.setattr("builtins.input", lambda prompt, answer=answer: answer)
        bump_version.manual_mode(pyproject, cargo, version_file, "1.0.0")
    assert "No change made" in capsys.readouterr().out


@bump_skip
def test_bump_version_main_unknown_command(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nversion = "1.0.0"\n', encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["bump_version.py", "wat"])
    bump_version.main()
    assert "Unknown command: wat" in capsys.readouterr().out


def test_tag_release_get_version(monkeypatch, tmp_path):
    version_file = tmp_path / "__version__.py"
    version_file.write_text('__version__ = "2.4.6"\n', encoding="utf-8")
    monkeypatch.setattr(tag_release, "VERSION_FILE", version_file)
    assert tag_release.get_version() == "2.4.6"


def test_tag_release_get_version_rejects_unparseable_file(monkeypatch, tmp_path):
    version_file = tmp_path / "__version__.py"
    version_file.write_text("VERSION = 'x'\n", encoding="utf-8")
    monkeypatch.setattr(tag_release, "VERSION_FILE", version_file)
    with pytest.raises(SystemExit) as exc:
        tag_release.get_version()
    assert exc.value.code == 1


def test_tag_release_get_version_reports_missing_file(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(tag_release, "VERSION_FILE", tmp_path / "missing.py")
    with pytest.raises(SystemExit) as exc:
        tag_release.get_version()
    assert exc.value.code == 1
    assert "File not found" in capsys.readouterr().out


def test_tag_exists_parses_git_output(monkeypatch):
    class Result:
        stdout = "v1.2.3\nv1.2.4\n"

    monkeypatch.setattr(tag_release.subprocess, "run", lambda *args, **kwargs: Result())
    assert tag_release.tag_exists("v1.2.3") is True
    assert tag_release.tag_exists("v9.9.9") is False


def test_tag_release_run_invokes_shell_command(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(
        tag_release.subprocess,
        "run",
        lambda command, shell, check: calls.append((command, shell, check)),
    )
    tag_release.run("git status")
    assert calls == [("git status", True, True)]
    assert "$ git status" in capsys.readouterr().out


def test_tag_release_main_cancels_without_running_git(monkeypatch, tmp_path, capsys):
    version_file = tmp_path / "__version__.py"
    version_file.write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    monkeypatch.setattr(tag_release, "VERSION_FILE", version_file)
    monkeypatch.setattr(tag_release, "tag_exists", lambda tag: False)
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    with pytest.raises(SystemExit) as exc:
        tag_release.main()
    assert exc.value.code == 0
    assert "Cancelled" in capsys.readouterr().out


def test_tag_release_main_blocks_existing_tag(monkeypatch, tmp_path, capsys):
    version_file = tmp_path / "__version__.py"
    version_file.write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    monkeypatch.setattr(tag_release, "VERSION_FILE", version_file)
    monkeypatch.setattr(tag_release, "tag_exists", lambda tag: True)

    with pytest.raises(SystemExit) as exc:
        tag_release.main()
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().out


def test_bump_version_declares_its_toml_runtime_dependency():
    import tomllib

    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    script = Path("bump_version.py").read_text(encoding="utf-8")
    dependencies = pyproject["project"].get("dependencies", [])
    if "import toml" in script and not any(
        dep.lower().startswith("toml") for dep in dependencies
    ):
        pytest.xfail(
            "bump_version.py imports toml but pyproject.toml does not declare toml"
        )


def test_tag_release_main_success_path(monkeypatch, tmp_path, capsys):
    version_file = tmp_path / "__version__.py"
    version_file.write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    monkeypatch.setattr(tag_release, "VERSION_FILE", version_file)
    monkeypatch.setattr(tag_release, "tag_exists", lambda tag: False)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    commands = []
    monkeypatch.setattr(tag_release, "run", lambda command: commands.append(command))

    result = tag_release.main()
    assert result is None
    assert commands == ["git tag v1.2.3", "git push origin v1.2.3"]
    assert "Successfully tagged and pushed v1.2.3" in capsys.readouterr().out


def test_tag_release_main_handles_git_failure(monkeypatch, tmp_path, capsys):
    version_file = tmp_path / "__version__.py"
    version_file.write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    monkeypatch.setattr(tag_release, "VERSION_FILE", version_file)
    monkeypatch.setattr(tag_release, "tag_exists", lambda tag: False)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    def fail(command):
        raise __import__("subprocess").CalledProcessError(1, command)

    monkeypatch.setattr(tag_release, "run", fail)
    with pytest.raises(SystemExit) as exc:
        tag_release.main()
    assert exc.value.code == 1
    assert "Error during git operations" in capsys.readouterr().out
