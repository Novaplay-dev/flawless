"""Configuration: ~/.config/flawless/config.toml"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, asdict, fields
from pathlib import Path

from . import SUPPORTED_LANGUAGES

VALID_MODELS = ("tiny", "base", "small", "medium", "large-v3", "large-v3-turbo")


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(base) / "flawless"


def config_path() -> Path:
    return config_dir() / "config.toml"


@dataclass
class Config:
    # Transcription language: en | de | sr | auto
    language: str = "auto"
    # Whisper model size. "small" is the sweet spot for German/Serbian on CPU.
    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    # Whisper emits Serbian in Cyrillic; set true to get latinica instead.
    serbian_latin: bool = True
    # Output mode: auto | type | clipboard
    #   auto      -> type with ydotool/wtype if available, else clipboard
    #   type      -> only type, error if no tool
    #   clipboard -> always copy + notify
    output: str = "auto"
    # Microphone device index or name ("" = system default)
    input_device: str = ""
    # Desktop notifications on record start/stop/result
    notifications: bool = True
    # Seconds of audio to keep at most per recording (safety cap)
    max_seconds: int = 120

    def validate(self) -> None:
        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"language must be one of {', '.join(SUPPORTED_LANGUAGES)}; got {self.language!r}"
            )
        if self.model not in VALID_MODELS:
            raise ValueError(
                f"model must be one of {', '.join(VALID_MODELS)}; got {self.model!r}"
            )
        if self.output not in ("auto", "type", "clipboard"):
            raise ValueError(f"output must be auto|type|clipboard; got {self.output!r}")
        if self.max_seconds < 1:
            raise ValueError("max_seconds must be >= 1")


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def save(cfg: Config, path: Path | None = None) -> Path:
    cfg.validate()
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k} = {_toml_value(v)}" for k, v in asdict(cfg).items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        return Config()
    with open(path, "rb") as f:
        data = tomllib.load(f)
    known = {f.name for f in fields(Config)}
    cfg = Config(**{k: v for k, v in data.items() if k in known})
    cfg.validate()
    return cfg
