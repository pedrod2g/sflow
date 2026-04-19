"""Global hotkeys + mouse button trigger.

Modes:
  1. Hold Ctrl+Alt (Option)        → normal recording (hold-to-talk)
  2. Double-tap Ctrl                → hands-free (tap Ctrl again to stop)
  3. Hold Ctrl+Shift                → Command Mode (transform selection via LLM)
  4. Hold configured mouse button   → normal recording (opt-in via settings)

Emits:
  - pressed / released          → regular transcription
  - command_pressed / command_released → command-mode flow
"""
import time
from pynput import keyboard, mouse
from PyQt6.QtCore import QObject, pyqtSignal
from config import DOUBLE_TAP_INTERVAL, get_setting


_MOUSE_BUTTON_MAP = {
    "middle": mouse.Button.middle,
    "x1": getattr(mouse.Button, "x1", None),
    "x2": getattr(mouse.Button, "x2", None),
}


class HotkeyListener(QObject):
    pressed = pyqtSignal()
    released = pyqtSignal()
    command_pressed = pyqtSignal()
    command_released = pyqtSignal()
    hub_requested = pyqtSignal()
    paste_last_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._ctrl_held = False
        self._alt_held = False
        self._shift_held = False
        self._cmd_held = False
        self._recording = False
        self._hands_free = False
        self._command_mode = False
        self._kb_listener: keyboard.Listener | None = None
        self._mouse_listener: mouse.Listener | None = None

        self._last_ctrl_press = 0.0
        self._ctrl_tap_count = 0

    def start(self):
        self._kb_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._kb_listener.daemon = True
        self._kb_listener.start()

        mb_name = get_setting("mouse_button_hotkey")
        if mb_name and _MOUSE_BUTTON_MAP.get(mb_name):
            try:
                self._mouse_listener = mouse.Listener(on_click=self._on_click)
                self._mouse_listener.daemon = True
                self._mouse_listener.start()
            except Exception as e:
                print(f"Mouse listener unavailable: {e}")

    def stop(self):
        if self._kb_listener:
            self._kb_listener.stop()
            self._kb_listener = None
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None

    # --- Mouse ---
    def _on_click(self, x, y, button, pressed):
        mb_name = get_setting("mouse_button_hotkey")
        target = _MOUSE_BUTTON_MAP.get(mb_name)
        if target is None or button != target:
            return
        if pressed and not self._recording:
            self._recording = True
            self._hands_free = False
            self.pressed.emit()
        elif not pressed and self._recording and not self._hands_free and not self._command_mode:
            self._recording = False
            self.released.emit()

    # --- Keyboard ---
    def _key_char(self, key):
        try:
            return (getattr(key, "char", None) or "").lower()
        except Exception:
            return ""

    def _on_press(self, key):
        is_ctrl = key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
        is_alt = key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
                         keyboard.Key.alt_gr)
        is_shift = key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
        is_cmd = key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r)

        if is_cmd:
            self._cmd_held = True
        elif is_ctrl:
            self._ctrl_held = True
            now = time.time()

            # Hands-free stop: single Ctrl tap while recording
            if self._hands_free and self._recording:
                self._hands_free = False
                self._recording = False
                self.released.emit()
                return

            if now - self._last_ctrl_press < DOUBLE_TAP_INTERVAL:
                self._ctrl_tap_count += 1
            else:
                self._ctrl_tap_count = 1
            self._last_ctrl_press = now

            if self._ctrl_tap_count >= 2 and not self._recording:
                self._ctrl_tap_count = 0
                self._hands_free = True
                self._recording = True
                self.pressed.emit()
                return

        elif is_alt:
            self._alt_held = True
        elif is_shift:
            self._shift_held = True

        # Global utility hotkeys (work even during recording? no — only when idle)
        if not self._recording:
            ch = self._key_char(key)
            # Cmd+Shift+H → open Hub
            if (self._cmd_held and self._shift_held and not self._ctrl_held
                    and not self._alt_held and ch == "h"
                    and get_setting("history_hotkey_enabled", True)):
                self.hub_requested.emit()
                return
            # Cmd+Ctrl+V → paste last transcript (Wispr Flow convention)
            if (self._cmd_held and self._ctrl_held and not self._shift_held
                    and not self._alt_held and ch == "v"):
                self.paste_last_requested.emit()
                return

        if self._recording:
            return

        # Command Mode: Ctrl+Shift (priority over Ctrl+Alt, require command_mode_enabled)
        if (self._ctrl_held and self._shift_held and not self._alt_held
                and get_setting("command_mode_enabled", True)):
            self._recording = True
            self._command_mode = True
            self._hands_free = False
            self.command_pressed.emit()
            return

        # Normal hold: Ctrl+Alt
        if self._ctrl_held and self._alt_held:
            self._recording = True
            self._hands_free = False
            self._command_mode = False
            self.pressed.emit()

    def _on_release(self, key):
        is_ctrl = key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
        is_alt = key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
                         keyboard.Key.alt_gr)
        is_shift = key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
        is_cmd = key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r)

        if is_cmd:
            self._cmd_held = False
        elif is_ctrl:
            self._ctrl_held = False
        elif is_alt:
            self._alt_held = False
        elif is_shift:
            self._shift_held = False

        if not self._recording or self._hands_free:
            return

        if self._command_mode:
            # Require Ctrl+Shift both held; release either ends command mode
            if not (self._ctrl_held and self._shift_held):
                self._recording = False
                self._command_mode = False
                self.command_released.emit()
            return

        # Normal hold ends when either Ctrl or Alt released
        if not (self._ctrl_held and self._alt_held):
            self._recording = False
            self.released.emit()
