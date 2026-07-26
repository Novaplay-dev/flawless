import pytest

from flawless import inject


def test_empty_text_rejected():
    with pytest.raises(inject.InjectError):
        inject.deliver("")


def test_clipboard_fallback(monkeypatch):
    monkeypatch.setattr(inject, "type_text", lambda text: False)
    monkeypatch.setattr(inject, "copy_to_clipboard", lambda text: True)
    assert inject.deliver("hello", "auto") == "clipboard"


def test_type_mode_fails_without_tool(monkeypatch):
    monkeypatch.setattr(inject, "type_text", lambda text: False)
    with pytest.raises(inject.InjectError, match="typing tool"):
        inject.deliver("hello", "type")


def test_typed_preferred(monkeypatch):
    monkeypatch.setattr(inject, "type_text", lambda text: True)
    assert inject.deliver("hello", "auto") == "typed"


def test_de_layout_swaps_physical_keys():
    # ydotool must be fed the US chars sharing the key with the German ones.
    assert inject.for_layout("Zylinder heiß?", "de") == "Yzlinder hei-_"
    assert inject.for_layout("Zylinder heiß?", "us") == "Zylinder heiß?"
    assert inject.for_layout("größer: 5-3", "de") == "gr;-er> 5/3"
