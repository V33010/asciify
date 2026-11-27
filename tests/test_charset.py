from __future__ import annotations

import json
from pathlib import Path

import pytest

from ascii_art import charset


@pytest.fixture()
def isolated_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    path = tmp_path / "config.json"
    monkeypatch.setattr(charset, "CONFIG_FILE", path)
    return path


def test_all_builtin_charsets_are_nonempty_strings():
    assert charset.CHARSETS
    for name, chars in charset.CHARSETS.items():
        assert isinstance(name, str)
        assert name
        assert isinstance(chars, str)
        assert chars, f"charset {name!r} is empty"


def test_get_charset_defaults_to_default_without_config(isolated_config):
    assert isolated_config.exists() is False
    assert charset.get_charset() == charset.CHARSETS["default"]


def test_get_charset_accepts_nonempty_custom_string(isolated_config):
    assert charset.get_charset("XYZ") == "XYZ"


def test_get_charset_rejects_truthy_non_string_custom_charset(isolated_config):
    with pytest.raises(ValueError, match="non-empty string"):
        charset.get_charset(123)


def test_persistent_charset_round_trip(isolated_config):
    charset.set_persistent_charset("blocks")

    assert isolated_config.exists()
    payload = json.loads(isolated_config.read_text(encoding="utf-8"))
    assert payload == {"charset": "blocks"}
    assert charset.load_persistent_charset_name() == "blocks"
    assert charset.get_charset() == charset.CHARSETS["blocks"]


def test_custom_charset_has_priority_over_persistent_charset(isolated_config):
    charset.set_persistent_charset("blocks")
    assert charset.get_charset("abc") == "abc"


def test_invalid_persistent_charset_name_raises(isolated_config):
    with pytest.raises(ValueError, match="Invalid charset"):
        charset.set_persistent_charset("does-not-exist")


def test_corrupt_config_is_treated_as_no_saved_preference(isolated_config):
    isolated_config.write_text("{not valid json", encoding="utf-8")
    assert charset.load_persistent_charset_name() is None
    assert charset.get_charset() == charset.CHARSETS["default"]


def test_unknown_saved_charset_is_ignored(isolated_config):
    isolated_config.write_text(json.dumps({"charset": "unknown"}), encoding="utf-8")
    assert charset.load_persistent_charset_name() == "unknown"
    assert charset.get_charset() == charset.CHARSETS["default"]


def test_set_persistent_charset_prints_success_message(isolated_config, capsys):
    charset.set_persistent_charset("binary")
    captured = capsys.readouterr().out
    assert "Default charset set to: binary" in captured


def test_set_persistent_charset_handles_write_failure(
    monkeypatch, isolated_config, capsys
):
    class BrokenFile:
        def __enter__(self):
            raise OSError("disk full")

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: BrokenFile())
    charset.set_persistent_charset("binary")
    captured = capsys.readouterr().out
    assert "Failed to save config" in captured
    assert "disk full" in captured


def test_empty_custom_charset_should_be_rejected():
    with pytest.raises(ValueError, match="non-empty string"):
        charset.get_charset("")


def test_builtin_charset_name_on_cli_style_custom_option_should_resolve():
    assert charset.get_charset("blocks") == charset.CHARSETS["blocks"]
