# Anti-Capture Secure Applications for Windows 10 & 11

Immune to screen capture, screenshots, and screen recording software (OBS Studio, Discord Screen Share, Zoom, Microsoft Teams, Snipping Tool, Game Bar, Lightshot, ShareX, etc.).

---

## What's Included

### 1. 🌐 Anti-Capture Browser (`anti_capture_browser.py`)
A full Chromium (Microsoft Edge WebView2) web browser with built-in anti-capture protection and **Screen Snipping + Google Search**:
- **Immune to Recording**: Screen recording software captures whatever is behind this browser window.
- **📸 Snip & Google**: Click to drag a rectangle anywhere on your screen. It automatically captures the area, puts it in the Windows Clipboard, and pastes it into Google / Google Lens to search immediately!
- **🖥️ Fullscreen Search**: Instantly snaps the full screen behind the window and searches it on Google.
- **📋 Paste Clipboard**: Pastes any image currently on your clipboard into Google's search bar.
- **Mode Switching**: Toggle between Ghost Mode (`0x11`), Blackout Mode (`0x01`), and Normal Mode (`0x00`).
- **Always on Top**: Pin the browser so it floats above all other apps while working.

**To run:** Double-click `run_anti_capture_browser.bat` or run:
```powershell
python anti_capture_browser.py
```

---

### 2. 🛡️ Anti-Capture Secure Workspace (`anti_capture_window.py`)
A lightweight, zero-dependency confidential scratchpad & notes window:
- Great for viewing passwords, tokens, API keys, or confidential documents.
- Includes mode switching and an instant screenshot test.

**To run:** Double-click `run_anti_capture.bat` or run:
```powershell
python anti_capture_window.py
```

---

### 3. ⚡ Standalone PowerShell Window (`AntiCaptureWindow.ps1`)
Runs natively via Windows PowerShell with zero dependencies.
- Right-click `AntiCaptureWindow.ps1` -> **Run with PowerShell**.

---

## How Screen Capture & Google Lens Paste Works

1. When you click **📸 Snip & Google** or **🖥️ Fullscreen Search**:
   - The desktop is captured using native Win32 GDI.
   - Because Windows DWM knows this browser window has `WDA_EXCLUDEFROMCAPTURE` (`0x11`), **this browser is excluded from the screenshot!**
2. The captured snippet is formatted as `CF_DIB` (Device Independent Bitmap) and placed in the Windows Clipboard.
3. The browser brings `https://www.google.com` to the foreground, focuses Google's image search / search bar, and dispatches a paste event.
4. Google Lens analyzes the image and returns visual search results instantly!
