import time
import win32gui
import win32con
import win32process
import pyperclip
from pynput import keyboard

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


def paste_text(text: str):
    """Copy text to clipboard and paste into the previously active app."""
    global _saved_hwnd

    # Copy to clipboard via pyperclip
    try:
        pyperclip.copy(text)
    except Exception as e:
        print(f"Error copying to clipboard: {e}")

    # Restore focus to the app that was active before recording
    if _saved_hwnd:
        try:
            # We try to restore if it's minimized, and switch focus
            win32gui.ShowWindow(_saved_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(_saved_hwnd)
            time.sleep(0.12)
        except Exception as e:
            print(f"Error restoring window focus: {e}")

    # Simulate Ctrl+V using pynput
    try:
        _keyboard.press(keyboard.Key.ctrl)
        _keyboard.press('v')
        time.sleep(0.05)
        _keyboard.release('v')
        _keyboard.release(keyboard.Key.ctrl)
    except Exception as e:
        print(f"Error simulating paste: {e}")

    _saved_hwnd = None
