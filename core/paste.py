"""Paste text into the foreground app. Two backends:

1. KEYSTROKE (default): CGEventKeyboardSetUnicodeString — inyecta el texto
   directamente como eventos de teclado Unicode. NO toca el clipboard del
   usuario. Más privacy-friendly y más rápido para strings pequeños.

2. CLIPBOARD (fallback): NSPasteboard + Cmd+V. Preserva y restaura el
   clipboard del usuario alrededor del paste, pero hay una ventana (~0.5s)
   donde otro listener podría leer el texto intermedio.

La elección se hace por setting `paste_backend` ("keystroke" | "clipboard").
"""
import sys
import time
from config import get_setting

_saved_app: str | None = None
_saved_hwnd: int | None = None
_saved_clipboard: str | None = None

if sys.platform == "win32":
    import win32gui
    import win32con
    import pyperclip
    from pynput import keyboard
    _keyboard = keyboard.Controller()
else:
    import subprocess


# ---------- Focus management ----------
def save_frontmost_app():
    global _saved_app, _saved_hwnd
    if sys.platform == "win32":
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                _saved_hwnd = hwnd
        except Exception as e:
            print(f"Error saving frontmost app: {e}")
    else:
        try:
            from AppKit import NSWorkspace
            active = NSWorkspace.sharedWorkspace().frontmostApplication()
            if active is not None:
                name = str(active.localizedName() or "")
                if name and name != "SFlow":
                    _saved_app = name
                    return
        except Exception:
            pass
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of first process whose frontmost is true'],
                capture_output=True, text=True, timeout=2,
            )
            name = result.stdout.strip()
            if name and name != "SFlow":
                _saved_app = name
        except Exception:
            pass


def _restore_focus():
    global _saved_app, _saved_hwnd
    if sys.platform == "win32":
        if _saved_hwnd:
            try:
                win32gui.ShowWindow(_saved_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(_saved_hwnd)
                time.sleep(0.12)
            except Exception as e:
                print(f"Error restoring window focus: {e}")
    else:
        if not _saved_app:
            return
        try:
            from AppKit import NSWorkspace
            ws = NSWorkspace.sharedWorkspace()
            for app in ws.runningApplications():
                if str(app.localizedName() or "") == _saved_app:
                    try:
                        app.activateWithOptions_(1 << 1)
                        time.sleep(0.08)
                        return
                    except Exception:
                        break
        except Exception:
            pass
        try:
            subprocess.run(
                ["osascript", "-e", f'tell application "{_saved_app}" to activate'],
                check=True, timeout=2,
            )
            time.sleep(0.12)
        except Exception:
            pass


# ---------- Clipboard (fallback path) ----------
def _clipboard_read() -> str:
    if sys.platform == "win32":
        try:
            return pyperclip.paste()
        except Exception:
            return ""
    else:
        try:
            from AppKit import NSPasteboard, NSPasteboardTypeString
            pb = NSPasteboard.generalPasteboard()
            val = pb.stringForType_(NSPasteboardTypeString)
            return str(val) if val else ""
        except Exception:
            try:
                r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=1)
                return r.stdout
            except Exception:
                return ""


def _clipboard_write(text: str):
    if sys.platform == "win32":
        try:
            pyperclip.copy(text)
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
    else:
        try:
            from AppKit import NSPasteboard, NSPasteboardTypeString
            pb = NSPasteboard.generalPasteboard()
            pb.clearContents()
            pb.setString_forType_(text, NSPasteboardTypeString)
        except Exception:
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


def _cmd_v():
    if sys.platform == "win32":
        try:
            _keyboard.press(keyboard.Key.ctrl)
            _keyboard.press('v')
            time.sleep(0.05)
            _keyboard.release('v')
            _keyboard.release(keyboard.Key.ctrl)
        except Exception as e:
            print(f"Error simulating paste: {e}")
    else:
        subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'],
            check=True,
        )


def _paste_via_clipboard(text: str):
    global _saved_clipboard
    _saved_clipboard = _clipboard_read()
    _clipboard_write(text)
    _restore_focus()
    _cmd_v()
    if _saved_clipboard is not None:
        def _restore():
            time.sleep(0.5)
            try:
                _clipboard_write(_saved_clipboard)
            except Exception:
                pass
        import threading
        threading.Thread(target=_restore, daemon=True).start()


# ---------- Keystroke injection (macOS only) ----------
def _type_via_cgevent(text: str) -> bool:
    if sys.platform == "win32":
        return False
    try:
        from Quartz import (
            CGEventCreateKeyboardEvent,
            CGEventKeyboardSetUnicodeString,
            CGEventPost,
            kCGHIDEventTap,
        )
    except Exception as e:
        print(f"CGEvent unavailable: {e}")
        return False

    CHUNK = 20
    i = 0
    n = len(text)
    while i < n:
        piece = text[i:i + CHUNK]
        down = CGEventCreateKeyboardEvent(None, 0, True)
        CGEventKeyboardSetUnicodeString(down, len(piece), piece)
        CGEventPost(kCGHIDEventTap, down)
        up = CGEventCreateKeyboardEvent(None, 0, False)
        CGEventKeyboardSetUnicodeString(up, len(piece), piece)
        CGEventPost(kCGHIDEventTap, up)
        i += CHUNK
        if i < n:
            time.sleep(0.004)
    return True


# ---------- Public API ----------
def paste_text(text: str):
    global _saved_app, _saved_hwnd
    if not text:
        _saved_app = None
        _saved_hwnd = None
        return

    backend = get_setting("paste_backend", "keystroke")
    streaming = get_setting("streaming_paste_enabled", False)

    _restore_focus()

    if sys.platform == "win32":
        if streaming and len(text) > 40:
            parts = []
            buf = ""
            for ch in text:
                buf += ch
                if ch == " " or ch == "\n":
                    parts.append(buf)
                    buf = ""
            if buf:
                parts.append(buf)

            chunk_size = 3
            chunks = ["".join(parts[i:i + chunk_size]) for i in range(0, len(parts), chunk_size)]
            for chunk in chunks:
                _clipboard_write(chunk)
                _cmd_v()
                time.sleep(0.025)
        else:
            _clipboard_write(text)
            _cmd_v()
    else:
        if backend == "keystroke":
            if streaming and len(text) > 40:
                parts = text.split(" ")
                for i, p in enumerate(parts):
                    chunk = p + (" " if i < len(parts) - 1 else "")
                    if not _type_via_cgevent(chunk):
                        _paste_via_clipboard(text[sum(len(x) + 1 for x in parts[:i]):])
                        break
                    time.sleep(0.02)
            else:
                ok = _type_via_cgevent(text)
                if not ok:
                    _paste_via_clipboard(text)
        else:
            _paste_via_clipboard(text)

    _saved_app = None
    _saved_hwnd = None


def paste_last_transcript(text: str):
    if sys.platform == "win32":
        _clipboard_write(text)
        _cmd_v()
    else:
        backend = get_setting("paste_backend", "keystroke")
        if backend == "keystroke":
            if not _type_via_cgevent(text):
                _clipboard_write(text)
                _cmd_v()
        else:
            _clipboard_write(text)
            _cmd_v()
