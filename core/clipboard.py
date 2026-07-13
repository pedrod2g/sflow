import time
import win32gui
import win32con
import win32process
import pyperclip
from pynput import keyboard
from config import get_setting

_saved_hwnd: int | None = None
_keyboard = keyboard.Controller()


def save_frontmost_app():
    """Save the currently focused application before recording starts."""
    global _saved_hwnd
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            _saved_hwnd = hwnd
    except Exception as e:
        print(f"Error saving frontmost app: {e}")


def _copy_to_clipboard(text: str):
    try:
        pyperclip.copy(text)
    except Exception as e:
        print(f"Error copying to clipboard: {e}")


def _restore_focus():
    global _saved_hwnd
    if _saved_hwnd:
        try:
            win32gui.ShowWindow(_saved_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(_saved_hwnd)
            time.sleep(0.12)
        except Exception as e:
            print(f"Error restoring window focus: {e}")


def _cmd_v():
    """Simulate Ctrl+V on Windows."""
    try:
        _keyboard.press(keyboard.Key.ctrl)
        _keyboard.press('v')
        time.sleep(0.05)
        _keyboard.release('v')
        _keyboard.release(keyboard.Key.ctrl)
    except Exception as e:
        print(f"Error simulating paste: {e}")


def paste_text(text: str):
    """Copy text to clipboard and paste into the previously active app.

    If streaming_paste_enabled, paste word-by-word for "live typing" UX.
    """
    global _saved_hwnd

    streaming = get_setting("streaming_paste_enabled", False)

    if not streaming or len(text) < 40:
        _copy_to_clipboard(text)
        _restore_focus()
        _cmd_v()
        _saved_hwnd = None
        return

    # Streaming paste: restore focus once, then paste chunks with tiny delay.
    _restore_focus()
    # Split on spaces but keep newlines intact
    parts = []
    buf = ""
    for ch in text:
        buf += ch
        if ch == " " or ch == "\n":
            parts.append(buf)
            buf = ""
    if buf:
        parts.append(buf)

    # Group into chunks of ~3 words to reduce paste count
    chunk_size = 3
    chunks = ["".join(parts[i:i + chunk_size]) for i in range(0, len(parts), chunk_size)]

    for chunk in chunks:
        _copy_to_clipboard(chunk)
        _cmd_v()
        time.sleep(0.025)  # ~25ms between chunks → ~40 cps, feels natural

    _saved_hwnd = None
