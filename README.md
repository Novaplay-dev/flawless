# Flawless

Local voice dictation for Linux, in the spirit of Wispr Flow: press a hotkey,
speak, press again — your words appear in whatever app has focus.

- **100% local & offline** — transcription runs on your machine with
  [faster-whisper](https://github.com/SYSTRAN/faster-whisper); nothing leaves it.
- **Languages:** English, German, Serbian, or auto-detect per utterance.
- Serbian comes out in **latinica** by default (Cyrillic optional).
- Works on **Wayland and X11** (KDE, GNOME, wlroots).

## Install

```bash
git clone https://github.com/Novaplay-dev/flawless.git ~/flawless
cd ~/flawless
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/flawless setup     # creates config + prints hotkey instructions
```

Optional but recommended for direct typing into apps:

```bash
sudo dnf install ydotool     # Fedora (ships a *system* service, not a user one)
# let your user own the daemon socket:
sudo mkdir -p /etc/systemd/system/ydotool.service.d
sudo tee /etc/systemd/system/ydotool.service.d/override.conf <<EOF
[Service]
ExecStart=
ExecStart=/usr/bin/ydotoold --socket-path=/tmp/.ydotool_socket --socket-own=$(id -u):$(id -g)
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now ydotool
ydotool type hello           # should type "hello"
```

Without a typing tool, Flawless copies the text to the clipboard and shows a
notification — just press `Ctrl+V`.

## Use

```bash
# 1. run the daemon (loads the model once, keeps the mic ready)
.venv/bin/flawless daemon &

# 2. bind a global hotkey (KDE: System Settings -> Keyboard -> Shortcuts ->
#    Add New -> Command) to:
~/flawless/.venv/bin/flawless toggle

# 3. hotkey -> speak -> hotkey. Done.
```

Autostart at every login (installs + enables a systemd user service):

```bash
.venv/bin/flawless autostart          # --disable to undo
```

## Keyboard layout

`ydotool` sends raw key positions, so on a **qwertz** keyboard a plain "y"
would arrive as "z". Flawless reads your layout from `localectl` and
compensates. Pin it if auto-detection is wrong:

```bash
flawless config --set keyboard_layout=de    # auto | us | de
```

## Commands

| Command | What it does |
|---|---|
| `flawless toggle` | start recording / stop + transcribe + deliver |
| `flawless cancel` | discard the current recording |
| `flawless lang en\|de\|sr\|auto` | switch language (with notification) |
| `flawless transcribe file.wav` | transcribe an audio file to stdout |
| `flawless config` | show config; `--set key=value` to change |
| `flawless devices` | list microphones |
| `flawless status` / `quit` | daemon state / shutdown |

## Configuration

`~/.config/flawless/config.toml` (created by `flawless setup`):

| Key | Default | Meaning |
|---|---|---|
| `language` | `auto` | `en`, `de`, `sr`, or `auto` |
| `model` | `small` | `tiny`…`large-v3-turbo`; `small` is a good CPU default for de/sr |
| `serbian_latin` | `true` | transliterate Whisper's Cyrillic output to latinica |
| `output` | `auto` | `type` (ydotool/wtype/xdotool), `clipboard`, or `auto` |
| `input_device` | default mic | index or name from `flawless devices` |
| `compute_type` | `int8` | use `float16` + `device = "cuda"` on an NVIDIA GPU |

The model (~460 MB for `small`) downloads automatically on first use and is
cached in `~/.cache/huggingface`.

## Tests

```bash
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest              # unit tests
.venv/bin/pytest -m e2e       # synthesizes speech with espeak-ng, transcribes it
```
