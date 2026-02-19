"""
NotchPrompt for Windows
=======================
A floating top-of-screen teleprompter overlay with system tray support.
Windows equivalent of https://github.com/saif0200/notchprompt

Requirements:
    pip install pystray pillow keyboard

Usage:
    python notchprompt_windows.py

Keyboard Shortcuts:
    Ctrl+Alt+P  - Start / Pause
    Ctrl+Alt+R  - Reset scroll
    Ctrl+Alt+J  - Jump back 5 seconds
    Ctrl+Alt+H  - Toggle overlay visibility
    Ctrl+Alt+=  - Increase speed
    Ctrl+Alt+-  - Decrease speed
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
import threading
import time
import sys
import os

# Optional imports (graceful fallback)
try:
    import pystray
    from PIL import Image, ImageDraw
    # Verify they're actually usable
    _test = Image.new("RGBA", (1, 1))
    HAS_TRAY = True
except Exception:
    HAS_TRAY = False
    print("[WARN] pystray/Pillow not found. System tray icon disabled.")
    print("       Install with: pip install pystray pillow")

try:
    import keyboard
    # Quick check it's usable
    keyboard.is_pressed  # attribute probe
    HAS_KEYBOARD = True
except Exception:
    HAS_KEYBOARD = False
    print("[WARN] keyboard not found. Global hotkeys disabled.")
    print("       Install with: pip install keyboard")


# ─────────────────────────────────────────────
#  Constants / defaults
# ─────────────────────────────────────────────
DEFAULT_SCRIPT = (
    "Welcome to NotchPrompt for Windows.\n\n"
    "This floating overlay sits at the top of your screen, "
    "just like the macOS notch version.\n\n"
    "Load your own script via File → Import Script, "
    "then press Start (▶) or Ctrl+Alt+P to begin scrolling.\n\n"
    "Adjust speed, font size, width, and height with the "
    "controls below the text area.\n\n"
    "Good luck with your presentation or recording!"
)

BG_COLOR        = "#111111"
TEXT_COLOR      = "#FFFFFF"
ACCENT_COLOR    = "#1E90FF"
CTRL_BG         = "#1A1A1A"
CTRL_FG         = "#CCCCCC"
OVERLAY_ALPHA   = 0.92        # window transparency (0‑1)
MIN_SPEED       = 10          # px / second
MAX_SPEED       = 300
DEFAULT_SPEED   = 60
DEFAULT_FONT_SZ = 28
DEFAULT_WIDTH   = 700
DEFAULT_HEIGHT  = 140
SCROLL_TICK_MS  = 16          # ~60 fps


# ─────────────────────────────────────────────
#  Helper: create a simple coloured tray icon
# ─────────────────────────────────────────────
def _make_tray_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, 60, 60], radius=12, fill=(30, 144, 255, 255))
    d.text((16, 16), "NP", fill="white")
    return img


# ─────────────────────────────────────────────
#  Main application
# ─────────────────────────────────────────────
class NotchPrompt:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()          # hide root; we use a Toplevel overlay

        # ── state ──────────────────────────────
        self.script_text  = DEFAULT_SCRIPT
        self.is_running   = False
        self.scroll_y     = 0.0       # fractional position (canvas units)
        self.speed        = DEFAULT_SPEED
        self.font_size    = DEFAULT_FONT_SZ
        self.overlay_w    = DEFAULT_WIDTH
        self.overlay_h    = DEFAULT_HEIGHT
        self.countdown_n  = 0         # 0 = disabled
        self.privacy_mode = False     # WS_EX_LAYERED trick (best-effort)
        self._scroll_job  = None
        self._cd_job      = None
        self._canvas_text_id = None
        self._canvas_h    = 0         # total canvas content height

        # ── Tk variables (bound to controls) ──
        self.var_speed    = tk.IntVar(value=self.speed)
        self.var_font_sz  = tk.IntVar(value=self.font_size)
        self.var_width    = tk.IntVar(value=self.overlay_w)
        self.var_height   = tk.IntVar(value=self.overlay_h)
        self.var_countdown= tk.IntVar(value=self.countdown_n)

        self._build_overlay()
        self._build_controls()
        self._update_canvas_text()

        if HAS_KEYBOARD:
            self._register_hotkeys()

        if HAS_TRAY:
            self._start_tray()

        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        self.root.mainloop()

    # ──────────────────────────────────────────
    #  Overlay window
    # ──────────────────────────────────────────
    def _build_overlay(self):
        self.overlay = tk.Toplevel(self.root)
        self.overlay.title("NotchPrompt")
        self.overlay.overrideredirect(True)      # no title bar
        self.overlay.attributes("-topmost", True)
        self.overlay.attributes("-alpha", OVERLAY_ALPHA)
        self.overlay.configure(bg=BG_COLOR)
        self.overlay.protocol("WM_DELETE_WINDOW", self._quit)

        # position: top-centre of primary monitor
        sw = self.overlay.winfo_screenwidth()
        x  = (sw - self.overlay_w) // 2
        self.overlay.geometry(f"{self.overlay_w}x{self.overlay_h}+{x}+0")

        # Canvas for scrolling text
        self.canvas = tk.Canvas(
            self.overlay,
            bg=BG_COLOR, highlightthickness=0,
            width=self.overlay_w, height=self.overlay_h
        )
        self.canvas.pack(fill="both", expand=True)

        # Arrow keys for horizontal nudging
        self.overlay.bind("<Left>",  lambda e: self._nudge(-10))
        self.overlay.bind("<Right>", lambda e: self._nudge(10))
        self.overlay.bind("<Shift-Left>",  lambda e: self._nudge(-50))
        self.overlay.bind("<Shift-Right>", lambda e: self._nudge(50))

        # Drag to reposition
        self.overlay.bind("<ButtonPress-1>",   self._drag_start)
        self.overlay.bind("<B1-Motion>",       self._drag_motion)
        self.canvas.bind("<ButtonPress-1>",    self._drag_start)
        self.canvas.bind("<B1-Motion>",        self._drag_motion)
        self._drag_ox = self._drag_oy = 0

        # Right-click context menu
        self._ctx = tk.Menu(self.overlay, tearoff=0, bg=CTRL_BG, fg=CTRL_FG)
        self._ctx.add_command(label="Open Controls", command=self._show_controls)
        self._ctx.add_separator()
        self._ctx.add_command(label="Quit", command=self._quit)
        self.canvas.bind("<Button-3>", self._show_ctx)
        self.overlay.bind("<Button-3>", self._show_ctx)

    def _drag_start(self, ev):
        self._drag_ox = ev.x_root - self.overlay.winfo_x()
        self._drag_oy = ev.y_root - self.overlay.winfo_y()
        self._pinned_to_top = self.overlay.winfo_y() <= 4  # treat ≤4px as "at top"

    def _drag_motion(self, ev):
        nx = ev.x_root - self._drag_ox
        if self._pinned_to_top:
            # Horizontal-only while snapped to top edge
            sw = self.overlay.winfo_screenwidth()
            nx = max(0, min(nx, sw - self.overlay_w))
            self.overlay.geometry(f"+{nx}+0")
        else:
            ny = ev.y_root - self._drag_oy
            self.overlay.geometry(f"+{nx}+{ny}")

    def _show_ctx(self, ev):
        self._ctx.tk_popup(ev.x_root, ev.y_root)

    # ──────────────────────────────────────────
    #  Controls window
    # ──────────────────────────────────────────
    def _build_controls(self):
        self.ctrl_win = tk.Toplevel(self.root)
        self.ctrl_win.title("NotchPrompt — Controls")
        self.ctrl_win.configure(bg=CTRL_BG)
        self.ctrl_win.resizable(False, False)
        self.ctrl_win.protocol("WM_DELETE_WINDOW", self._hide_controls)

        # Position below overlay
        sw = self.ctrl_win.winfo_screenwidth()
        cx = (sw - 520) // 2
        self.ctrl_win.geometry(f"520x420+{cx}+160")

        # ── script area ────────────────────────
        frm_script = tk.Frame(self.ctrl_win, bg=CTRL_BG)
        frm_script.pack(fill="both", expand=True, padx=10, pady=(10, 4))

        tk.Label(frm_script, text="Script", bg=CTRL_BG, fg=CTRL_FG,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.txt = tk.Text(
            frm_script, height=8, bg="#222", fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR, relief="flat",
            font=("Segoe UI", 10), wrap="word", undo=True
        )
        self.txt.pack(fill="both", expand=True)
        self.txt.insert("1.0", self.script_text)
        self.txt.bind("<<Modified>>", self._on_script_changed)

        # File buttons
        frm_file = tk.Frame(self.ctrl_win, bg=CTRL_BG)
        frm_file.pack(fill="x", padx=10, pady=2)
        _btn(frm_file, "📂 Import", self._import_script).pack(side="left", padx=2)
        _btn(frm_file, "💾 Export", self._export_script).pack(side="left", padx=2)

        # ── sliders ────────────────────────────
        frm_sliders = tk.Frame(self.ctrl_win, bg=CTRL_BG)
        frm_sliders.pack(fill="x", padx=10, pady=4)

        self._slider_row(frm_sliders, "Speed (px/s)",  self.var_speed,    MIN_SPEED, MAX_SPEED,  self._on_speed_change,    0)
        self._slider_row(frm_sliders, "Font size",      self.var_font_sz,  10, 72,    self._on_font_change,     1)
        self._slider_row(frm_sliders, "Overlay width",  self.var_width,    200, 1800, self._on_size_change,     2)
        self._slider_row(frm_sliders, "Overlay height", self.var_height,   60, 400,   self._on_size_change,     3)
        self._slider_row(frm_sliders, "Countdown (s)",  self.var_countdown,0, 10,     lambda *_: None,          4)

        # ── transport ──────────────────────────
        frm_transport = tk.Frame(self.ctrl_win, bg=CTRL_BG)
        frm_transport.pack(pady=8)

        self.btn_play  = _btn(frm_transport, "▶  Start",      self.toggle_play,  accent=True)
        self.btn_reset = _btn(frm_transport, "⏮  Reset",      self.reset_scroll)
        self.btn_back  = _btn(frm_transport, "⏪  −5s",        self.jump_back)
        self.btn_priv  = _btn(frm_transport, "🔒 Privacy OFF", self.toggle_privacy)

        for b in (self.btn_play, self.btn_reset, self.btn_back, self.btn_priv):
            b.pack(side="left", padx=4)

        # ── position controls ──────────────────
        frm_pos = tk.Frame(self.ctrl_win, bg=CTRL_BG)
        frm_pos.pack(pady=(0, 4))
        tk.Label(frm_pos, text="Position:", bg=CTRL_BG, fg=CTRL_FG,
                 font=("Segoe UI", 9)).pack(side="left", padx=(0,6))
        _btn(frm_pos, "⬅ ◀",  lambda: self._nudge(-50)).pack(side="left", padx=2)
        _btn(frm_pos, "◀",    lambda: self._nudge(-10)).pack(side="left", padx=2)
        _btn(frm_pos, "▶",    lambda: self._nudge(10)).pack(side="left", padx=2)
        _btn(frm_pos, "▶ ➡", lambda: self._nudge(50)).pack(side="left", padx=2)
        _btn(frm_pos, "⬆ Snap to Top", self._snap_to_top).pack(side="left", padx=8)
        _btn(frm_pos, "⬛ Centre",      self._centre_overlay).pack(side="left", padx=2)

        # Hotkey hint
        hint = ("Ctrl+Alt+P  Play/Pause   |   Ctrl+Alt+R  Reset   |   "
                "Ctrl+Alt+J  −5s   |   Ctrl+Alt+H  Show/Hide")
        tk.Label(self.ctrl_win, text=hint, bg=CTRL_BG, fg="#555",
                 font=("Segoe UI", 8)).pack(pady=(0, 6))

    def _slider_row(self, parent, label, var, lo, hi, cmd, row):
        tk.Label(parent, text=label, bg=CTRL_BG, fg=CTRL_FG,
                 font=("Segoe UI", 9), width=16, anchor="w"
                 ).grid(row=row, column=0, padx=(0,6), pady=2, sticky="w")
        s = ttk.Scale(parent, from_=lo, to=hi, variable=var,
                      orient="horizontal", length=280, command=cmd)
        s.grid(row=row, column=1, sticky="ew")
        lbl = tk.Label(parent, textvariable=var, bg=CTRL_BG, fg=ACCENT_COLOR,
                       font=("Segoe UI", 9), width=4)
        lbl.grid(row=row, column=2, padx=(6,0))

    def _nudge(self, dx):
        """Move overlay horizontally by dx pixels, clamped to screen width."""
        x = self.overlay.winfo_x() + dx
        y = self.overlay.winfo_y()
        sw = self.overlay.winfo_screenwidth()
        x = max(0, min(x, sw - self.overlay_w))
        self.overlay.geometry(f"+{x}+{y}")

    def _snap_to_top(self):
        """Snap overlay to y=0, keeping current x."""
        x = self.overlay.winfo_x()
        sw = self.overlay.winfo_screenwidth()
        x = max(0, min(x, sw - self.overlay_w))
        self.overlay.geometry(f"+{x}+0")

    def _centre_overlay(self):
        """Centre the overlay horizontally at the top."""
        sw = self.overlay.winfo_screenwidth()
        x = (sw - self.overlay_w) // 2
        y = self.overlay.winfo_y()
        self.overlay.geometry(f"+{x}+{y}")

    def _show_controls(self):
        self.ctrl_win.deiconify()
        self.ctrl_win.lift()

    def _hide_controls(self):
        self.ctrl_win.withdraw()

    # ──────────────────────────────────────────
    #  Canvas / text rendering
    # ──────────────────────────────────────────
    def _update_canvas_text(self):
        """Redraw the text item on the canvas with current settings."""
        self.canvas.delete("all")
        self._canvas_text_id = self.canvas.create_text(
            self.overlay_w // 2,
            self.overlay_h // 2 - int(self.scroll_y),
            text=self.script_text,
            fill=TEXT_COLOR,
            font=("Segoe UI", self.font_size),
            width=self.overlay_w - 40,
            anchor="n",
            justify="center",
        )
        # measure total text height
        bb = self.canvas.bbox(self._canvas_text_id)
        if bb:
            self._canvas_h = bb[3] - bb[1]

    def _scroll_step(self):
        if not self.is_running:
            return
        px_per_tick = self.speed * SCROLL_TICK_MS / 1000.0
        self.scroll_y += px_per_tick

        # move the existing text item (fast, no redraw)
        self.canvas.moveto(
            self._canvas_text_id,
            self.overlay_w // 2 - self.canvas.bbox(self._canvas_text_id)[2] // 2
            if self._canvas_text_id else 0,
            self.overlay_h // 2 - int(self.scroll_y),
        )
        # Stop at end
        bb = self.canvas.bbox(self._canvas_text_id)
        if bb and bb[3] < 0:
            self._stop()
            return

        self._scroll_job = self.overlay.after(SCROLL_TICK_MS, self._scroll_step)

    def _do_scroll_step(self):
        """Simpler move via coords update."""
        if not self.is_running:
            return
        px_per_tick = self.speed * SCROLL_TICK_MS / 1000.0
        self.scroll_y += px_per_tick
        # Update y of text item
        bb = self.canvas.bbox(self._canvas_text_id)
        if bb:
            cur_x = (bb[0] + bb[2]) / 2
            cur_y = bb[1]
            new_y = cur_y - px_per_tick
            self.canvas.coords(self._canvas_text_id, cur_x, new_y)
            if bb[3] < 0:          # scrolled completely past top
                self._stop()
                return
        self._scroll_job = self.overlay.after(SCROLL_TICK_MS, self._do_scroll_step)

    # ──────────────────────────────────────────
    #  Transport
    # ──────────────────────────────────────────
    def toggle_play(self):
        if self.is_running:
            self._stop()
        else:
            self._start()

    def _start(self):
        cd = self.var_countdown.get()
        if cd > 0:
            self._run_countdown(cd)
        else:
            self._begin_scroll()

    def _run_countdown(self, n):
        self.canvas.delete("countdown")
        if n <= 0:
            self._begin_scroll()
            return
        self.canvas.create_text(
            self.overlay_w // 2, self.overlay_h // 2,
            text=str(n), fill=ACCENT_COLOR,
            font=("Segoe UI", 60, "bold"),
            tags="countdown"
        )
        self._cd_job = self.overlay.after(1000, lambda: self._run_countdown(n - 1))

    def _begin_scroll(self):
        self.canvas.delete("countdown")
        self.is_running = True
        self.btn_play.config(text="⏸  Pause")
        self._do_scroll_step()

    def _stop(self):
        self.is_running = False
        if self._scroll_job:
            self.overlay.after_cancel(self._scroll_job)
            self._scroll_job = None
        self.btn_play.config(text="▶  Start")

    def reset_scroll(self):
        was_running = self.is_running
        self._stop()
        self.scroll_y = 0.0
        self._update_canvas_text()
        if was_running:
            self._begin_scroll()

    def jump_back(self):
        """Jump back 5 seconds worth of scrolling."""
        px = self.speed * 5
        self.scroll_y = max(0.0, self.scroll_y - px)
        self._update_canvas_text()

    def toggle_privacy(self):
        """
        Best-effort screen capture exclusion.
        Works on Windows 10 2004+ via SetWindowDisplayAffinity.
        """
        self.privacy_mode = not self.privacy_mode
        try:
            import ctypes
            hwnd = self.overlay.winfo_id()
            # WDA_EXCLUDEFROMCAPTURE = 0x00000011
            affinity = 0x00000011 if self.privacy_mode else 0x00000000
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, affinity)
        except Exception:
            pass
        label = "🔒 Privacy ON" if self.privacy_mode else "🔒 Privacy OFF"
        self.btn_priv.config(text=label)

    def toggle_overlay_visibility(self):
        if self.overlay.winfo_viewable():
            self.overlay.withdraw()
        else:
            self.overlay.deiconify()
            self.overlay.lift()

    # ──────────────────────────────────────────
    #  Change handlers
    # ──────────────────────────────────────────
    def _on_script_changed(self, *_):
        self.txt.edit_modified(False)
        self.script_text = self.txt.get("1.0", "end-1c")
        was_running = self.is_running
        self._stop()
        self.scroll_y = 0.0
        self._update_canvas_text()

    def _on_speed_change(self, *_):
        self.speed = self.var_speed.get()

    def _on_font_change(self, *_):
        self.font_size = self.var_font_sz.get()
        was_running = self.is_running
        self._stop()
        self._update_canvas_text()

    def _on_size_change(self, *_):
        self.overlay_w = self.var_width.get()
        self.overlay_h = self.var_height.get()
        sw = self.overlay.winfo_screenwidth()
        x  = self.overlay.winfo_x()
        y  = self.overlay.winfo_y()
        self.overlay.geometry(f"{self.overlay_w}x{self.overlay_h}+{x}+{y}")
        self.canvas.config(width=self.overlay_w, height=self.overlay_h)
        was_running = self.is_running
        self._stop()
        self._update_canvas_text()

    # ──────────────────────────────────────────
    #  Speed shortcuts
    # ──────────────────────────────────────────
    def speed_up(self):
        self.speed = min(MAX_SPEED, self.speed + 10)
        self.var_speed.set(self.speed)

    def speed_down(self):
        self.speed = max(MIN_SPEED, self.speed - 10)
        self.var_speed.set(self.speed)

    # ──────────────────────────────────────────
    #  File I/O
    # ──────────────────────────────────────────
    def _import_script(self):
        path = filedialog.askopenfilename(
            title="Import Script",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.txt.delete("1.0", "end")
            self.txt.insert("1.0", content)
            self.script_text = content
            self.scroll_y = 0.0
            self._update_canvas_text()

    def _export_script(self):
        path = filedialog.asksaveasfilename(
            title="Export Script",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.txt.get("1.0", "end-1c"))
            messagebox.showinfo("Exported", f"Script saved to:\n{path}")

    # ──────────────────────────────────────────
    #  Global hotkeys
    # ──────────────────────────────────────────
    def _register_hotkeys(self):
        def safe(fn):
            return lambda: self.root.after(0, fn)

        keyboard.add_hotkey("ctrl+alt+p", safe(self.toggle_play))
        keyboard.add_hotkey("ctrl+alt+r", safe(self.reset_scroll))
        keyboard.add_hotkey("ctrl+alt+j", safe(self.jump_back))
        keyboard.add_hotkey("ctrl+alt+h", safe(self.toggle_overlay_visibility))
        keyboard.add_hotkey("ctrl+alt+=", safe(self.speed_up))
        keyboard.add_hotkey("ctrl+alt+-", safe(self.speed_down))

    # ──────────────────────────────────────────
    #  System tray
    # ──────────────────────────────────────────
    def _start_tray(self):
        icon_img = _make_tray_icon()
        menu = pystray.Menu(
            pystray.MenuItem("Show Controls", lambda: self.root.after(0, self._show_controls)),
            pystray.MenuItem("Play / Pause",  lambda: self.root.after(0, self.toggle_play)),
            pystray.MenuItem("Reset",         lambda: self.root.after(0, self.reset_scroll)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit",          lambda: self.root.after(0, self._quit)),
        )
        self.tray_icon = pystray.Icon("NotchPrompt", icon_img, "NotchPrompt", menu)
        t = threading.Thread(target=self.tray_icon.run, daemon=True)
        t.start()

    # ──────────────────────────────────────────
    #  Quit
    # ──────────────────────────────────────────
    def _quit(self):
        self._stop()
        if HAS_TRAY:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        if HAS_KEYBOARD:
            keyboard.unhook_all()
        self.root.destroy()


# ─────────────────────────────────────────────
#  Widget helper
# ─────────────────────────────────────────────
def _btn(parent, text, cmd, accent=False):
    bg = ACCENT_COLOR if accent else "#2A2A2A"
    fg = "white"
    return tk.Button(
        parent, text=text, command=cmd,
        bg=bg, fg=fg, activebackground="#1565C0" if accent else "#333",
        activeforeground="white", relief="flat", padx=10, pady=5,
        font=("Segoe UI", 9), cursor="hand2", borderwidth=0
    )


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    NotchPrompt()
