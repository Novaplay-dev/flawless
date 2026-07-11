"""Command-line interface for Flawless."""

from __future__ import annotations

import argparse
import sys

from . import SUPPORTED_LANGUAGES, __version__
from .config import Config, config_path, load, save


def _client_command(command: str) -> int:
    from .ipc import send_command

    try:
        print(send_command(command))
        return 0
    except (ConnectionError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _cmd_daemon(args) -> int:
    from .daemon import Daemon

    return Daemon().run(preload=not args.no_preload)


def _cmd_transcribe(args) -> int:
    from .transcriber import Transcriber

    cfg = load()
    if args.language:
        cfg.language = args.language
    text = Transcriber(cfg).transcribe_file(args.file)
    print(text)
    return 0


def _cmd_config(args) -> int:
    cfg = load()
    if not args.set:
        for key, value in vars(cfg).items():
            print(f"{key} = {value}")
        print(f"\n({config_path()})")
        return 0
    for pair in args.set:
        key, sep, value = pair.partition("=")
        if not sep:
            print(f"error: expected key=value, got {pair!r}", file=sys.stderr)
            return 1
        if not hasattr(cfg, key):
            print(f"error: unknown key {key!r}", file=sys.stderr)
            return 1
        current = getattr(cfg, key)
        if isinstance(current, bool):
            value = value.lower() in ("1", "true", "yes", "on")
        elif isinstance(current, int):
            value = int(value)
        setattr(cfg, key, value)
    try:
        save(cfg)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"saved {config_path()}")
    return 0


def _cmd_devices(args) -> int:
    from .audio import list_devices

    print(list_devices())
    return 0


def _cmd_setup(args) -> int:
    import shutil

    cfg_file = config_path()
    if not cfg_file.exists():
        save(Config())
        print(f"created {cfg_file}")
    print(
        f"""
Flawless {__version__} — setup

1. Start the daemon (or install the systemd service, see README):
     flawless daemon &

2. Bind a global hotkey to toggle dictation.
   KDE:   System Settings -> Keyboard -> Shortcuts -> Add New -> Command:
            flawless toggle
          (suggested key: Meta+H)
   GNOME: Settings -> Keyboard -> Custom Shortcuts -> command: flawless toggle

3. Press the hotkey, speak, press again. Text is typed into the focused
   window, or copied to the clipboard (notification tells you to Ctrl+V).

Languages: {', '.join(f'{k} ({v})' for k, v in SUPPORTED_LANGUAGES.items())}
Switch anytime:   flawless lang de
Direct typing:    install ydotool + enable ydotoold (else clipboard is used)
"""
    )
    typers = []
    try:
        from .inject import available_typers

        typers = available_typers()
    except Exception:
        pass
    if typers:
        print(f"typing tool detected: {', '.join(typers)} — text will be typed directly")
    else:
        print("no typing tool detected — falling back to clipboard + Ctrl+V")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="flawless",
        description="Local voice dictation (English, German, Serbian).",
    )
    parser.add_argument("--version", action="version", version=f"flawless {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("daemon", help="run the dictation daemon")
    p.add_argument("--no-preload", action="store_true", help="don't load the model at startup")
    p.set_defaults(func=_cmd_daemon)

    for name, help_text in [
        ("toggle", "start recording / stop + transcribe + deliver"),
        ("start", "start recording"),
        ("stop", "stop recording and transcribe"),
        ("cancel", "discard the current recording"),
        ("status", "show daemon state"),
        ("quit", "stop the daemon"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(func=lambda a, n=name: _client_command(n.upper()))

    p = sub.add_parser("lang", help="switch language")
    p.add_argument("code", choices=sorted(SUPPORTED_LANGUAGES))
    p.set_defaults(
        func=lambda a: _client_command(f"LANG {a.code}")
        if _daemon_running()
        else _set_lang_offline(a.code)
    )

    p = sub.add_parser("transcribe", help="transcribe an audio file and print the text")
    p.add_argument("file")
    p.add_argument("-l", "--language", choices=sorted(SUPPORTED_LANGUAGES))
    p.set_defaults(func=_cmd_transcribe)

    p = sub.add_parser("config", help="show or change configuration")
    p.add_argument("--set", metavar="KEY=VALUE", action="append", help="set a config value")
    p.set_defaults(func=_cmd_config)

    p = sub.add_parser("devices", help="list audio input devices")
    p.set_defaults(func=_cmd_devices)

    p = sub.add_parser("setup", help="first-run setup instructions")
    p.set_defaults(func=_cmd_setup)

    args = parser.parse_args(argv)
    return args.func(args)


def _daemon_running() -> bool:
    from .ipc import socket_path

    return socket_path().exists()


def _set_lang_offline(code: str) -> int:
    cfg = load()
    cfg.language = code
    save(cfg)
    print(f"language set to {code} ({SUPPORTED_LANGUAGES[code]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
