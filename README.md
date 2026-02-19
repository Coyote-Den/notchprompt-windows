# NotchPrompt for Windows

> A floating top-of-screen teleprompter overlay for Windows — inspired by [notchprompt](https://github.com/saif0200/notchprompt) for macOS.

![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows)
![License](https://img.shields.io/badge/license-MIT-green)

Since Windows has no notch, the overlay anchors to the **top of your screen** and slides horizontally — keeping your script right at the top of your field of vision during presentations and recordings.

---

## Screenshot

```
┌─────────────────────────────────────────────────────┐  ← top of screen
│  Welcome to NotchPrompt. This floating overlay sits  │
│  at the top of your screen. Load your script and     │
│  press Start to begin scrolling...                   │
└─────────────────────────────────────────────────────┘
```

---

## Features

- 🪟 **Floating overlay** — always-on-top, anchored to the top of your screen
- ↔️ **Horizontal drag** — drag left/right along the top edge, or use nudge buttons / arrow keys
- 🖱️ **System tray** — `NP` tray icon with quick-access menu
- ⏯️ **Transport controls** — Play/Pause, Reset, Jump back 5 s
- ⏱️ **Countdown timer** — optional 1–10 s countdown before scrolling starts
- 🔠 **Adjustable** — speed, font size, overlay width, height & opacity (all via sliders)
- 💾 **Save Settings** — persist all settings to disk and restore them automatically on next launch
- 📄 **Import / Export** — plain `.txt` scripts
- 🔒 **Privacy mode** — hides overlay from screen capture via `SetWindowDisplayAffinity` (Windows 10 2004+)
- ⌨️ **Global hotkeys** — work even when another app has focus

---

## Requirements

- **Python 3.9+** — `tkinter` is included in the standard Windows installer
- Optional (strongly recommended):

```
pip install pystray pillow keyboard
```

> **Tip:** If packages seem installed but still show warnings, use
> `python -m pip install pystray pillow keyboard` to ensure they install into
> the correct interpreter.

---

## Run

```bash
python notchprompt_windows.py
```

The overlay appears at the top-centre of your screen. The Controls window opens below it.

> **Global hotkeys** may require running as Administrator on some systems.

---

## Controls

### Sliders

| Slider | Range | Description |
|--------|-------|-------------|
| Speed | 10 – 300 px/s | How fast the text scrolls |
| Font size | 10 – 72 pt | Text size on the overlay |
| Overlay width | 200 – 1800 px | Horizontal size of the overlay |
| Overlay height | 60 – 400 px | Vertical size of the overlay |
| Countdown | 0 – 10 s | Delay before scrolling starts |
| Opacity | 0.10 – 1.00 | Overlay transparency (live preview) |

### Transport

| Button | Action |
|--------|--------|
| ▶ Start / ⏸ Pause | Toggle scrolling |
| ⏮ Reset | Return to top of script |
| ⏪ −5s | Jump back 5 seconds of scroll |
| 🔒 Privacy | Toggle screen-capture exclusion |

### Position

| Button | Action |
|--------|--------|
| ◀ / ▶ | Nudge overlay 10 px left/right |
| ⬅◀ / ▶➡ | Nudge overlay 50 px left/right |
| ⬆ Snap to Top | Pin overlay back to y = 0 |
| ⬛ Centre | Centre overlay horizontally |

---

## Moving the Overlay

| Method | How |
|--------|-----|
| **Drag** | Click & drag — locked to horizontal when at the top edge |
| **Arrow keys** | Click overlay to focus, then `←` / `→` (10 px), `Shift+←` / `Shift+→` (50 px) |
| **Nudge buttons** | ◀ / ▶ (10 px), ⬅◀ / ▶➡ (50 px) in the Controls window |
| **Centre** | ⬛ Centre button snaps it back to the middle |
| **Snap to Top** | ⬆ Snap to Top pins y back to 0 |

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Alt+P` | Start / Pause |
| `Ctrl+Alt+R` | Reset scroll |
| `Ctrl+Alt+J` | Jump back 5 seconds |
| `Ctrl+Alt+H` | Show / Hide overlay |
| `Ctrl+Alt+=` | Increase speed |
| `Ctrl+Alt+-` | Decrease speed |

---

## Save Settings

Click **💾 Save Settings** in the Controls window to persist your current setup. On next launch, everything is restored automatically — no extra steps needed.

Settings are saved to:
```
%APPDATA%\NotchPrompt\settings.json
```

The following are saved and restored:

| Setting | Saved |
|---------|-------|
| Speed | ✅ |
| Font size | ✅ |
| Overlay width & height | ✅ |
| Countdown | ✅ |
| Opacity | ✅ |
| Privacy mode (on/off) | ✅ |
| Overlay position (x, y) | ✅ |
| Controls window position | ✅ |
| Script text | ✅ |

---

## Privacy Mode

Clicking **🔒 Privacy** calls `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)`, making the overlay invisible to screen recorders and capture software. Requires Windows 10 version 2004 or later. Works on a best-effort, app-dependent basis — same caveat as the macOS original.

---

## Project Structure

```
notchprompt-windows/
├── notchprompt_windows.py   # main application
├── requirements.txt          # optional dependencies
├── LICENSE                   # MIT
└── README.md
```

---

## Contributing

PRs welcome! Some ideas:

- [ ] Packaged `.exe` via PyInstaller
- [ ] Multi-monitor awareness
- [ ] Font chooser
- [ ] Rich text / Markdown script support

---

## Credits

Inspired by [notchprompt](https://github.com/saif0200/notchprompt) by [@saif0200](https://github.com/saif0200).

---

## License

MIT — see [LICENSE](LICENSE).
