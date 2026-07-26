"""Deliver transcribed text to the focused application.

Preference order (output = "auto"):
  1. ydotool type   (works everywhere if ydotoold is running)
  2. wtype          (wlroots compositors)
  3. xdotool type   (X11 sessions only)
  4. clipboard      (wl-copy / xclip) + notification to press Ctrl+V
"""

from __future__ import annotations

import os
import shutil
import subprocess


class InjectError(RuntimeError):
    pass


# ydotool injects raw evdev keycodes picked from a built-in US table; the
# compositor then applies the *real* layout, so on a German qwertz keyboard
# "y" arrives as "z". Fix: hand ydotool the US character that sits on the same
# physical key as the character we actually want.
# (wtype/xdotool ship their own keymap and need no translation.)
_PHYSICAL_KEYS = {
    "de": {
        "y": "z", "z": "y", "Y": "Z", "Z": "Y",
        "ß": "-", "?": "_", "ü": "[", "Ü": "{", "ö": ";", "Ö": ":",
        "ä": "'", "Ä": '"', "+": "]", "*": "}", "#": "\\", "'": "|",
        "-": "/", "_": "?", ";": "<", ":": ">", '"': "@", "§": "#",
        "&": "^", "/": "&", "(": "*", ")": "(", "=": ")", "^": "`", "°": "~",
    }
}
# ponytail: AltGr-only chars (@ € [ ] { } \ | < >) have no US single-key
# equivalent and stay wrong on de; add a keycode+modifier sender if they matter.


def _detect_layout() -> str:
    """Layout configured for this machine, e.g. 'de'. Empty when unknown."""
    # ponytail: system-wide layout only; a per-window KDE/GNOME switcher isn't
    # followed. Set keyboard_layout in config.toml to pin it.
    try:
        out = subprocess.run(
            ["localectl", "status"], capture_output=True, text=True, timeout=5
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""
    for line in out.splitlines():
        if "Layout:" in line:
            return line.split(":", 1)[1].strip().split(",")[0]
    return ""


def keyboard_layout() -> str:
    from .config import load

    try:
        layout = load().keyboard_layout
    except Exception:
        layout = "auto"
    return _detect_layout() if layout == "auto" else layout


def for_layout(text: str, layout: str | None = None) -> str:
    """Translate text into the US characters ydotool must send on `layout`."""
    keys = _PHYSICAL_KEYS.get(keyboard_layout() if layout is None else layout)
    return text.translate(str.maketrans(keys)) if keys else text


def _run(cmd: list[str], input_text: str | None = None) -> bool:
    env = os.environ.copy()
    # Fedora runs ydotoold as a system service; its socket lives in /tmp.
    env.setdefault("YDOTOOL_SOCKET", "/tmp/.ydotool_socket")
    try:
        proc = subprocess.run(
            cmd,
            input=input_text.encode() if input_text is not None else None,
            capture_output=True,
            timeout=15,
            env=env,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(
        os.environ.get("WAYLAND_DISPLAY")
    )


def available_typers() -> list[str]:
    tools = []
    if shutil.which("ydotool"):
        tools.append("ydotool")
    if shutil.which("wtype") and _is_wayland():
        tools.append("wtype")
    if shutil.which("xdotool") and not _is_wayland():
        tools.append("xdotool")
    return tools


def type_text(text: str) -> bool:
    """Try to type text directly into the focused window."""
    for tool in available_typers():
        if tool == "ydotool" and _run(["ydotool", "type", "--", for_layout(text)]):
            return True
        if tool == "wtype" and _run(["wtype", "--", text]):
            return True
        if tool == "xdotool" and _run(
            ["xdotool", "type", "--clearmodifiers", "--", text]
        ):
            return True
    return False


def copy_to_clipboard(text: str) -> bool:
    if shutil.which("wl-copy") and _run(["wl-copy"], input_text=text):
        return True
    if shutil.which("xclip") and _run(
        ["xclip", "-selection", "clipboard"], input_text=text
    ):
        return True
    return False


def deliver(text: str, mode: str = "auto") -> str:
    """Deliver text; returns how it was delivered: 'typed' or 'clipboard'.

    Raises InjectError when nothing worked.
    """
    if not text:
        raise InjectError("nothing to deliver (empty transcription)")
    if mode in ("auto", "type") and type_text(text):
        return "typed"
    if mode == "type":
        raise InjectError(
            "no typing tool worked; install ydotool (and enable ydotoold) or wtype"
        )
    if copy_to_clipboard(text):
        return "clipboard"
    raise InjectError("could not type or copy — install ydotool, wtype, or wl-clipboard")
