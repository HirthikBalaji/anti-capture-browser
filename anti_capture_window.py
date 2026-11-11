import sys
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Windows Win32 API constants
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Windows 10 (2004+) & Windows 11

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Function prototypes
user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
user32.GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowDisplayAffinity.restype = wintypes.BOOL
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND

GA_ROOT = 2

class AntiCaptureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🛡️ Anti-Capture Secure Window")
        self.root.geometry("750x550")
        self.root.minsize(550, 400)

        # Dark theme styling
        self.bg_color = "#1e1e2e"
        self.card_color = "#282a36"
        self.accent_color = "#bd93f9"
        self.text_color = "#f8f8f2"
        self.highlight_green = "#50fa7b"
        self.root.configure(bg=self.bg_color)

        self.root_hwnd = None
        self.current_affinity = WDA_EXCLUDEFROMCAPTURE

        self._build_ui()
        self.root.update_idletasks()
        self._init_window_protection()

    def _get_root_hwnd(self):
        child_hwnd = self.root.winfo_id()
        top_hwnd = user32.GetAncestor(child_hwnd, GA_ROOT)
        return top_hwnd or child_hwnd

    def _init_window_protection(self):
        self.root_hwnd = self._get_root_hwnd()
        self.set_protection(WDA_EXCLUDEFROMCAPTURE)

    def set_protection(self, affinity_code):
        if not self.root_hwnd:
            self.root_hwnd = self._get_root_hwnd()

        success = user32.SetWindowDisplayAffinity(self.root_hwnd, affinity_code)
        if success:
            self.current_affinity = affinity_code
            self._update_status_ui()
        else:
            err = ctypes.GetLastError()
            messagebox.showerror("Error", f"Failed to set window display affinity. Error code: {err}")

    def _update_status_ui(self):
        if self.current_affinity == WDA_EXCLUDEFROMCAPTURE:
            self.status_badge.config(
                text="● GHOST MODE ACTIVE (Completely Invisible to Capture)",
                fg="#50fa7b",
                bg="#213b2c"
            )
            self.desc_label.config(
                text="In screenshots and recordings (OBS, Discord, Snipping Tool, Zoom, etc.), "
                     "this window is completely transparent — whatever is behind it will be recorded instead!"
            )
        elif self.current_affinity == WDA_MONITOR:
            self.status_badge.config(
                text="● BLACKOUT MODE ACTIVE (Captures as Black Box)",
                fg="#ffb86c",
                bg="#3d2d1e"
            )
            self.desc_label.config(
                text="This window will appear as an opaque black rectangle in screenshots and screen recordings."
            )
        else:
            self.status_badge.config(
                text="○ UNPROTECTED (Normally Visible in Capture)",
                fg="#ff5555",
                bg="#3d1e1e"
            )
            self.desc_label.config(
                text="Standard window mode. The window will be visible in all screenshots and recordings."
            )

    def toggle_always_on_top(self):
        current = bool(self.root.attributes("-topmost"))
        self.root.attributes("-topmost", not current)
        self.topmost_btn.config(text="📌 Always on Top: ON" if not current else "📌 Always on Top: OFF")

    def test_screenshot(self):
        """Take a test capture of the desktop area where this window is located and verify exclusion."""
        self.root.update()
        x = self.root.winfo_rootx() + 50
        y = self.root.winfo_rooty() + 50

        # Grab pixel from screen
        hdc = user32.GetDC(0)
        pixel = gdi32.GetPixel(hdc, x, y)
        user32.ReleaseDC(0, hdc)

        b = (pixel >> 16) & 0xFF
        g = (pixel >> 8) & 0xFF
        r = pixel & 0xFF

        msg = (
            f"Protection is active!\n\n"
            f"Test pixel sampled at screen coordinate ({x}, {y}):\n"
            f"Captured Color: RGB({r}, {g}, {b})\n\n"
            f"Notice: Try taking a screenshot right now using:\n"
            f" • Windows + Shift + S (Snipping Tool)\n"
            f" • Print Screen key\n"
            f" • OBS Studio / Discord Screen Share\n\n"
            f"This window will NOT appear in the capture!"
        )
        messagebox.showinfo("Anti-Capture Test", msg)

    def clear_text(self):
        self.text_area.delete("1.0", tk.END)

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt;*.md;*.json;*.py;*.env"), ("All files", "*.*")]
        )
        if path:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", content)

    def save_file(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt;*.md;*.json;*.py;*.env"), ("All files", "*.*")]
        )
        if path:
            content = self.text_area.get("1.0", tk.END)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    def _build_ui(self):
        # Header frame
        header_frame = tk.Frame(self.root, bg=self.card_color, padx=16, pady=12)
        header_frame.pack(fill=tk.X, padx=14, pady=(14, 8))

        title_label = tk.Label(
            header_frame,
            text="🛡️ Anti-Capture Secure Workspace",
            font=("Segoe UI", 14, "bold"),
            fg=self.text_color,
            bg=self.card_color
        )
        title_label.pack(anchor="w")

        self.status_badge = tk.Label(
            header_frame,
            text="",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=4
        )
        self.status_badge.pack(anchor="w", pady=(6, 2))

        self.desc_label = tk.Label(
            header_frame,
            text="",
            font=("Segoe UI", 9),
            fg="#a6adc8",
            bg=self.card_color,
            wraplength=680,
            justify="left"
        )
        self.desc_label.pack(anchor="w", pady=(2, 0))

        # Toolbar Frame
        toolbar = tk.Frame(self.root, bg=self.bg_color)
        toolbar.pack(fill=tk.X, padx=14, pady=6)

        # Mode Buttons
        btn_style = {"font": ("Segoe UI", 9, "bold"), "relief": "flat", "padx": 10, "pady": 4, "cursor": "hand2"}

        btn_ghost = tk.Button(
            toolbar,
            text="👻 Ghost Mode (Invisible)",
            bg="#2e5339",
            fg="#50fa7b",
            activebackground="#3b6949",
            command=lambda: self.set_protection(WDA_EXCLUDEFROMCAPTURE),
            **btn_style
        )
        btn_ghost.pack(side=tk.LEFT, padx=(0, 6))

        btn_black = tk.Button(
            toolbar,
            text="⬛ Blackout Mode",
            bg="#4d3822",
            fg="#ffb86c",
            activebackground="#664a2d",
            command=lambda: self.set_protection(WDA_MONITOR),
            **btn_style
        )
        btn_black.pack(side=tk.LEFT, padx=6)

        btn_none = tk.Button(
            toolbar,
            text="👁️ Allow Capture (Off)",
            bg="#4a2424",
            fg="#ff5555",
            activebackground="#663131",
            command=lambda: self.set_protection(WDA_NONE),
            **btn_style
        )
        btn_none.pack(side=tk.LEFT, padx=6)

        self.topmost_btn = tk.Button(
            toolbar,
            text="📌 Always on Top: OFF",
            bg="#36384a",
            fg=self.text_color,
            activebackground="#44475a",
            command=self.toggle_always_on_top,
            **btn_style
        )
        self.topmost_btn.pack(side=tk.LEFT, padx=6)

        test_btn = tk.Button(
            toolbar,
            text="🧪 Test Protection",
            bg="#3d375a",
            fg="#bd93f9",
            activebackground="#4f4675",
            command=self.test_screenshot,
            **btn_style
        )
        test_btn.pack(side=tk.RIGHT)

        # Text editor / secure content area
        editor_frame = tk.Frame(self.root, bg=self.bg_color)
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(4, 10))

        # Editor header
        file_bar = tk.Frame(editor_frame, bg=self.bg_color)
        file_bar.pack(fill=tk.X, pady=(0, 4))

        lbl_edit = tk.Label(
            file_bar,
            text="Confidential Notes & Clipboard (Anything here cannot be captured/recorded):",
            font=("Segoe UI", 9),
            fg="#cdd6f4",
            bg=self.bg_color
        )
        lbl_edit.pack(side=tk.LEFT)

        btn_clear = tk.Button(file_bar, text="Clear", bg="#36384a", fg=self.text_color, relief="flat", padx=6, command=self.clear_text)
        btn_clear.pack(side=tk.RIGHT, padx=2)

        btn_save = tk.Button(file_bar, text="Save File", bg="#36384a", fg=self.text_color, relief="flat", padx=6, command=self.save_file)
        btn_save.pack(side=tk.RIGHT, padx=2)

        btn_open = tk.Button(file_bar, text="Open File", bg="#36384a", fg=self.text_color, relief="flat", padx=6, command=self.open_file)
        btn_open.pack(side=tk.RIGHT, padx=2)

        # Scrollable Text Area
        scrollbar = tk.Scrollbar(editor_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_area = tk.Text(
            editor_frame,
            bg=self.card_color,
            fg=self.text_color,
            insertbackground=self.highlight_green,
            selectbackground="#44475a",
            selectforeground=self.text_color,
            font=("Consolas", 11),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            relief="flat",
            padx=12,
            pady=10
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_area.yview)

        sample_text = (
            "🔐 CONFIDENTIAL SECURE WORKSPACE\n"
            "================================\n\n"
            "This window uses the Windows Desktop Window Manager (DWM) display affinity API:\n"
            "  -> SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)\n\n"
            "Try it now:\n"
            "1. Press [Win + Shift + S] to take a screenshot with the Windows Snipping Tool.\n"
            "2. Open OBS Studio, Discord screen share, Zoom, or Teams.\n"
            "3. Look at the preview/recording: this window is 100% INVISIBLE!\n"
            "   (Whatever wallpaper or application is behind this window will be captured instead).\n\n"
            "You can safely view or edit:\n"
            "  • Passwords and API tokens\n"
            "  • Secret keys & private credentials\n"
            "  • Sensitive personal documents\n"
            "  • Confidential conversations or cheat notes\n"
        )
        self.text_area.insert("1.0", sample_text)

def main():
    root = tk.Tk()
    app = AntiCaptureApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
