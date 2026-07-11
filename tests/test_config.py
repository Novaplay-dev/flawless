import pytest

from flawless.config import Config, load, save


def test_defaults_valid():
    Config().validate()


def test_roundtrip(tmp_path):
    cfg = Config(language="sr", model="tiny", serbian_latin=False, max_seconds=30)
    path = tmp_path / "config.toml"
    save(cfg, path)
    loaded = load(path)
    assert loaded == cfg


def test_missing_file_gives_defaults(tmp_path):
    assert load(tmp_path / "nope.toml") == Config()


def test_invalid_language_rejected():
    with pytest.raises(ValueError, match="language"):
        Config(language="fr").validate()


def test_invalid_output_rejected():
    with pytest.raises(ValueError, match="output"):
        Config(output="teleport").validate()


def test_unknown_keys_ignored(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('language = "de"\nfuture_option = true\n')
    assert load(path).language == "de"
