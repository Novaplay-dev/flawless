"""End-to-end: synthesize speech with espeak-ng, transcribe with the tiny model.

Slow (downloads ~75 MB model on first run). Run with: pytest -m e2e
"""

import shutil
import subprocess

import pytest

from flawless.config import Config
from flawless.transcriber import Transcriber

pytestmark = pytest.mark.e2e

needs_espeak = pytest.mark.skipif(
    not shutil.which("espeak-ng"), reason="espeak-ng not installed"
)


def synth(text: str, voice: str, path: str) -> None:
    subprocess.run(
        ["espeak-ng", "-v", voice, "-s", "140", "-w", path, text],
        check=True,
        capture_output=True,
    )


@needs_espeak
@pytest.mark.parametrize(
    "voice,lang,text,expect_word",
    [
        ("en", "en", "Hello, this is a test of the dictation system.", "test"),
        ("de", "de", "Guten Tag, das ist ein Test.", "test"),
    ],
)
def test_transcribe_synthesized(tmp_path, voice, lang, text, expect_word):
    wav = str(tmp_path / "sample.wav")
    synth(text, voice, wav)
    cfg = Config(model="tiny", language=lang)
    result = Transcriber(cfg).transcribe_file(wav)
    assert expect_word in result.lower()
