"""Flawless — local voice dictation for Linux.

Press a hotkey, speak, press again: your words are transcribed locally
with Whisper and delivered to the focused application.
Supported languages: English, German, Serbian (plus auto-detect).
"""

__version__ = "0.1.0"

SUPPORTED_LANGUAGES = {
    "en": "English",
    "de": "German (Deutsch)",
    "sr": "Serbian (Srpski)",
    "auto": "Auto-detect",
}
