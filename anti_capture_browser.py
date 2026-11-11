import sys
import os
import io
import time
import base64
import threading
import ctypes
from ctypes import wintypes
from PIL import Image

# Enable Per-Monitor DPI awareness before GUI creation
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import webview
import win32clipboard
import tkinter as tk

# .NET / WinForms imports for Toolbar integration
import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
from System import Action
from System.Windows.Forms import (
    ToolStrip, ToolStripButton, ToolStripTextBox, ToolStripLabel,
    ToolStripSeparator, DockStyle, Keys, Padding, ToolStripGripStyle
)
from System.Drawing import Color, Font, FontStyle, SystemFonts

# Win32 Constants
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Windows 10 (2004+) & Windows 11

GA_ROOT = 2
VK_CONTROL = 0x11
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Win32 Function Signatures
user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
user32.GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowDisplayAffinity.restype = wintypes.BOOL
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL


def capture_fullscreen():
    """Captures the full desktop screen using GDI.
    Because the browser window has WDA_EXCLUDEFROMCAPTURE, it will NOT appear in the capture!
    """
    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)

    hdesktop = user32.GetDesktopWindow()
    hdc_src = user32.GetWindowDC(hdesktop)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_src)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_src, width, height)
    gdi32.SelectObject(hdc_mem, hbmp)

    SRCCOPY = 0x00CC0020
    gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_src, 0, 0, SRCCOPY)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ('biSize', wintypes.DWORD),
            ('biWidth', wintypes.LONG),
            ('biHeight', wintypes.LONG),
            ('biPlanes', wintypes.WORD),
            ('biBitCount', wintypes.WORD),
            ('biCompression', wintypes.DWORD),
            ('biSizeImage', wintypes.DWORD),
            ('biXPelsPerMeter', wintypes.LONG),
            ('biYPelsPerMeter', wintypes.LONG),
            ('biClrUsed', wintypes.DWORD),
            ('biClrImportant', wintypes.DWORD)
        ]

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = width
    bmi.biHeight = -height  # top-down DIB
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0

    buf = (ctypes.c_char * (width * height * 4))()
    gdi32.GetDIBits(hdc_mem, hbmp, 0, height, ctypes.byref(buf), ctypes.byref(bmi), 0)

    img = Image.frombuffer('RGBA', (width, height), buf, 'raw', 'BGRA', 0, 1)

    # Cleanup GDI handles
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hdesktop, hdc_src)

    return img.convert('RGB')


def set_image_to_clipboard(pil_image):
    """Copies a PIL Image into the Windows Clipboard as CF_DIB."""
    output = io.BytesIO()
    rgb_img = pil_image.convert('RGB')
    rgb_img.save(output, 'BMP')
    data = output.getvalue()[14:]  # Remove the 14-byte BITMAPFILEHEADER
    output.close()

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    finally:
        win32clipboard.CloseClipboard()


class InteractiveSnipper:
    """Semi-transparent full-screen overlay for drag-and-drop region capture."""
    def __init__(self, bg_image, callback):
        self.bg_image = bg_image
        self.callback = callback
        self.start_x = None
        self.start_y = None
        self.rect_id = None

        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.28)  # Subtle translucent overlay
        self.root.config(bg='black', cursor='cross')

        self.canvas = tk.Canvas(self.root, cursor='cross', bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Instructions banner
        self.canvas.create_text(
            self.root.winfo_screenwidth() // 2, 40,
            text="✂️ Drag to select an area to search on Google | Press ESC to cancel",
            fill="white", font=("Segoe UI", 16, "bold")
        )

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#50fa7b", width=2, fill="#bd93f9", stipple="gray25"
        )

    def on_drag(self, event):
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        end_x = event.x
        end_y = event.y
        self.root.destroy()

        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        # Only crop if selection has a meaningful size
        if (x2 - x1) > 10 and (y2 - y1) > 10:
            # Scale coordinates to native background image size
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            img_w, img_h = self.bg_image.size

            scale_x = img_w / screen_w
            scale_y = img_h / screen_h

            crop_box = (
                int(x1 * scale_x),
                int(y1 * scale_y),
                int(x2 * scale_x),
                int(y2 * scale_y)
            )
            cropped = self.bg_image.crop(crop_box)
            self.callback(cropped)


class AntiCaptureBrowser:
    def __init__(self):
        self.window = None
        self.hwnd = None
        self.current_affinity = WDA_EXCLUDEFROMCAPTURE
        self.url_box = None
        self.status_btn = None
        self.topmost_btn = None

    def start(self):
        # Create pywebview browser window pointing to Google
        self.window = webview.create_window(
            title="🛡️ Anti-Capture Browser (Immune to Screen Recording & Screenshots)",
            url="https://www.google.com",
            width=1100,
            height=750,
            min_size=(600, 450)
        )
        webview.start(self._on_app_ready, self.window)

    def _on_app_ready(self, window):
        time.sleep(0.5)
        # Extract native HWND from WinForms Form
        try:
            raw_hwnd = int(self.window.native.Handle.ToInt64())
            self.hwnd = wintypes.HWND(raw_hwnd)
        except Exception as e:
            print("Error retrieving native HWND:", e)
            return

        # 1. Apply Anti-Capture Display Affinity
        self.set_protection(WDA_EXCLUDEFROMCAPTURE)

        # 2. Attach Native Toolbar
        self._build_winforms_toolbar()

    def set_protection(self, affinity):
        if not self.hwnd:
            return
        success = user32.SetWindowDisplayAffinity(self.hwnd, affinity)
        if success:
            self.current_affinity = affinity
            self._update_status_ui()
        else:
            err = ctypes.GetLastError()
            print("Failed to set display affinity. Code:", err)

    def _update_status_ui(self):
        if not self.status_btn:
            return

        def update():
            if self.current_affinity == WDA_EXCLUDEFROMCAPTURE:
                self.status_btn.Text = "👻 Ghost Mode (Active)"
                self.status_btn.BackColor = Color.FromArgb(46, 83, 57)
                self.status_btn.ForeColor = Color.FromArgb(80, 250, 123)
                self.status_btn.ToolTipText = "Window is completely invisible in all screenshots and recordings (OBS, Discord, Zoom, Snipping Tool, etc.)."
            elif self.current_affinity == WDA_MONITOR:
                self.status_btn.Text = "⬛ Blackout Mode"
                self.status_btn.BackColor = Color.FromArgb(77, 56, 34)
                self.status_btn.ForeColor = Color.FromArgb(255, 184, 108)
                self.status_btn.ToolTipText = "Window renders as a solid black box in screen captures."
            else:
                self.status_btn.Text = "👁️ Unprotected"
                self.status_btn.BackColor = Color.FromArgb(74, 36, 36)
                self.status_btn.ForeColor = Color.FromArgb(255, 85, 85)
                self.status_btn.ToolTipText = "Standard mode: window can be captured normally."

        self.window.native.Invoke(Action(update))

    def _cycle_protection(self):
        if self.current_affinity == WDA_EXCLUDEFROMCAPTURE:
            self.set_protection(WDA_MONITOR)
        elif self.current_affinity == WDA_MONITOR:
            self.set_protection(WDA_NONE)
        else:
            self.set_protection(WDA_EXCLUDEFROMCAPTURE)

    def _toggle_topmost(self):
        def update():
            current = self.window.native.TopMost
            self.window.native.TopMost = not current
            self.topmost_btn.Text = "📌 Top: ON" if not current else "📌 Top: OFF"
            self.topmost_btn.ForeColor = Color.FromArgb(80, 250, 123) if not current else Color.White
        self.window.native.Invoke(Action(update))

    def _build_winforms_toolbar(self):
        def setup():
            ts = ToolStrip()
            ts.Dock = DockStyle.Top
            ts.BackColor = Color.FromArgb(30, 30, 46)
            ts.ForeColor = Color.White
            ts.Padding = Padding(6, 4, 6, 4)
            ts.GripStyle = ToolStripGripStyle.Hidden

            # Custom styling helper
            def style_btn(text, bg_rgb, fg_rgb):
                btn = ToolStripButton(text)
                btn.BackColor = Color.FromArgb(*bg_rgb)
                btn.ForeColor = Color.FromArgb(*fg_rgb)
                btn.Font = Font("Segoe UI", 9, FontStyle.Bold)
                btn.Margin = Padding(2, 1, 2, 1)
                return btn

            # 1. Protection Toggle Button
            self.status_btn = style_btn("👻 Ghost Mode (Active)", (46, 83, 57), (80, 250, 123))
            self.status_btn.Click += lambda sender, args: self._cycle_protection()
            ts.Items.Add(self.status_btn)

            # Separator
            ts.Items.Add(ToolStripSeparator())

            # 2. Snip & Search on Google Button
            snip_btn = style_btn("📸 Snip & Google", (61, 55, 90), (189, 147, 249))
            snip_btn.ToolTipText = "Snip any region on your screen and automatically search it with Google Lens!"
            snip_btn.Click += lambda sender, args: threading.Thread(target=self.trigger_snip_and_search).start()
            ts.Items.Add(snip_btn)

            # 3. Full Screen & Search Button
            full_btn = style_btn("🖥️ Fullscreen Search", (42, 60, 85), (139, 233, 253))
            full_btn.ToolTipText = "Capture entire screen behind this window and paste into Google search!"
            full_btn.Click += lambda sender, args: threading.Thread(target=self.trigger_fullscreen_and_search).start()
            ts.Items.Add(full_btn)

            # 4. Paste Current Clipboard to Google
            paste_btn = style_btn("📋 Paste Clipboard", (55, 55, 65), (248, 248, 242))
            paste_btn.ToolTipText = "Paste the image currently in your Windows Clipboard into Google search!"
            paste_btn.Click += lambda sender, args: threading.Thread(target=self.paste_image_to_google).start()
            ts.Items.Add(paste_btn)

            # Separator
            ts.Items.Add(ToolStripSeparator())

            # 5. Browser Navigation Controls
            back_btn = ToolStripButton("◀")
            back_btn.ForeColor = Color.White
            back_btn.Font = Font("Segoe UI", 9, FontStyle.Bold)
            back_btn.Click += lambda sender, args: self.window.evaluate_js("window.history.back()")
            ts.Items.Add(back_btn)

            fwd_btn = ToolStripButton("▶")
            fwd_btn.ForeColor = Color.White
            fwd_btn.Font = Font("Segoe UI", 9, FontStyle.Bold)
            fwd_btn.Click += lambda sender, args: self.window.evaluate_js("window.history.forward()")
            ts.Items.Add(fwd_btn)

            reload_btn = ToolStripButton("⟳")
            reload_btn.ForeColor = Color.White
            reload_btn.Font = Font("Segoe UI", 10, FontStyle.Bold)
            reload_btn.Click += lambda sender, args: self.window.evaluate_js("window.location.reload()")
            ts.Items.Add(reload_btn)

            home_btn = ToolStripButton("🏠 Google")
            home_btn.ForeColor = Color.White
            home_btn.Click += lambda sender, args: self.window.load_url("https://www.google.com")
            ts.Items.Add(home_btn)

            # 6. Address Bar
            self.url_box = ToolStripTextBox()
            self.url_box.Text = "https://www.google.com"
            self.url_box.Width = 320
            self.url_box.BackColor = Color.FromArgb(40, 42, 54)
            self.url_box.ForeColor = Color.White
            self.url_box.KeyDown += self._on_url_keydown
            ts.Items.Add(self.url_box)

            go_btn = ToolStripButton("Go")
            go_btn.ForeColor = Color.FromArgb(80, 250, 123)
            go_btn.Font = Font("Segoe UI", 9, FontStyle.Bold)
            go_btn.Click += lambda sender, args: self._navigate_to_url(self.url_box.Text)
            ts.Items.Add(go_btn)

            # 7. Always on Top Toggle
            self.topmost_btn = ToolStripButton("📌 Top: OFF")
            self.topmost_btn.ForeColor = Color.White
            self.topmost_btn.Click += lambda sender, args: self._toggle_topmost()
            ts.Items.Add(self.topmost_btn)

            # Add ToolStrip to window controls
            self.window.native.Controls.Add(ts)
            ts.SendToBack()

        self.window.native.Invoke(Action(setup))

    def _on_url_keydown(self, sender, args):
        if args.KeyCode == Keys.Enter:
            self._navigate_to_url(sender.Text)
            args.Handled = True

    def _navigate_to_url(self, url):
        target = url.strip()
        if not target.startswith("http://") and not target.startswith("https://"):
            target = "https://" + target
        self.window.load_url(target)

    # -------------------------------------------------------------
    # Screen Capture & Google Lens Paste Automation
    # -------------------------------------------------------------
    def trigger_snip_and_search(self):
        """Captures full background screen and shows interactive cropping overlay."""
        # 1. Grab screen (browser is excluded by DWM!)
        bg = capture_fullscreen()

        # 2. Launch interactive snip selector
        def on_crop(cropped_img):
            set_image_to_clipboard(cropped_img)
            self.paste_image_to_google()

        # Run Tkinter snip overlay in its own thread loop
        def run_snipper():
            snipper = InteractiveSnipper(bg, on_crop)
            snipper.root.mainloop()

        snipper_thread = threading.Thread(target=run_snipper)
        snipper_thread.start()

    def trigger_fullscreen_and_search(self):
        """Captures entire screen behind the window and searches Google."""
        full_img = capture_fullscreen()
        set_image_to_clipboard(full_img)
        self.paste_image_to_google()

    def paste_image_to_google(self):
        """Ensures browser is on Google, focuses search bar, and simulates paste."""
        # Check current URL
        curr_url = self.window.get_current_url() or ""
        if "google.com" not in curr_url.lower():
            self.window.load_url("https://www.google.com")
            time.sleep(1.2)

        # 1. Bring window to front
        if self.hwnd:
            user32.SetForegroundWindow(self.hwnd)
        time.sleep(0.2)

        # 2. Focus Google search bar or trigger Lens button via JavaScript
        js_focus = """
        (function() {
            // Click Google Lens camera button if present
            const lensBtn = document.querySelector('div[aria-label*="Search by image" i], div[aria-label*="image" i]');
            if (lensBtn) {
                lensBtn.click();
            }
            // Focus search input or active textarea
            const input = document.querySelector('textarea[name="q"], input[name="q"]');
            if (input) {
                input.focus();
            }
        })();
        """
        try:
            self.window.evaluate_js(js_focus)
        except Exception:
            pass

        time.sleep(0.3)

        # 3. Send hardware Ctrl+V keystroke to trigger paste
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def main():
    browser = AntiCaptureBrowser()
    browser.start()


if __name__ == "__main__":
    main()
