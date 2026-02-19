# NotchPrompt for Windows

A floating top-of-screen teleprompter overlay — the Windows equivalent of
[notchprompt](https://github.com/saif0200/notchprompt) for macOS.

Since Windows has no notch, the overlay anchors to the **top-centre** of your
primary monitor and can be dragged anywhere.

---

## Features

| Feature | Details |
|---|---|
| Floating overlay | Always-on-top, semi-transparent, top-centred |
| System tray icon | `NP` tray icon with quick-access menu |
| Transport controls | Play/Pause, Reset, Jump back 5 s |
| Adjustable speed | 10 – 300 px/s via slider |
| Adjustable font size | 10 – 72 pt |
| Adjustable overlay size | Width 200–1800 px, Height 60–400 px |
| Optional countdown | 0–10 s countdown before scrolling |
| Import / Export | Plain `.txt` scripts |
| Privacy mode | `SetWindowDisplayAffinity` — excludes overlay from screen capture (Windows 10 2004+) |
| Global hotkeys | Works even when another app has focus |

---

## Requirements

- **Python 3.9+** (tkinter ships with the standard Windows installer)
- Optional but recommended packages:

```
pip install pystray pillow keyboard
```

The app runs without these; you just lose the tray icon and global hotkeys.

---

## Run

```
python notchprompt_windows.py
```

The overlay appears at the top of your screen and the Controls window opens
below it.

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Alt+P` | Start / Pause |
| `Ctrl+Alt+R` | Reset scroll |
| `Ctrl+Alt+J` | Jump back 5 seconds |
| `Ctrl+Alt+H` | Show / Hide overlay |
| `Ctrl+Alt+=` | Increase speed |
| `Ctrl+Alt+-` | Decrease speed |

> **Note:** Global hotkeys require the `keyboard` package and may need the
> script to be run as Administrator on some systems.

---

## Privacy Mode

Clicking **Privacy** (or `Ctrl+Alt+H`) calls `SetWindowDisplayAffinity` with
`WDA_EXCLUDEFROMCAPTURE` so the overlay is invisible to screen-capture
software. This requires Windows 10 version 2004 or later and works on a
best-effort / app-dependent basis (same caveat as the macOS original).

---

## Drag & Reposition

Click and drag the overlay anywhere on screen. Right-click for a context menu.

---

## License

MIT — same as the original notchprompt.
