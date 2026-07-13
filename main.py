#!/usr/bin/env python3
"""SFlow - Voice-to-text desktop tool powered by Groq Whisper."""

import os
import sys
import traceback

# Hide console window immediately on Windows if frozen
if sys.platform == "win32" and getattr(sys, "frozen", False):
    import ctypes
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)

try:
    # Redirect stdout/stderr to log file on Windows GUI to prevent PyInstaller crashes
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        app_data_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SFlow")
        os.makedirs(app_data_dir, exist_ok=True)
        # Use buffering=1 (line buffered)
        f = open(os.path.join(app_data_dir, "sflow_output.log"), "w", buffering=1, encoding="utf-8")
        sys.stdout = f
        sys.stderr = f
except Exception:
    pass

try:
    import signal
    import subprocess
    import threading
    from PyQt6.QtWidgets import (
        QApplication, QSystemTrayIcon, QMenu,
        QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    )
    from PyQt6.QtCore import Qt, QObject, pyqtSignal, pyqtSlot
    from PyQt6.QtGui import QIcon, QPixmap, QAction

    from ui.pill_widget import PillWidget
    from core.recorder import AudioRecorder
    from core.transcriber import Transcriber
    from core.hotkey import HotkeyListener
    from core.clipboard import paste_text, save_frontmost_app
    from db.database import TranscriptionDB
    from web.server import start_web_server
    from config import LOGO_PATH, APP_DATA_DIR, GROQ_API_KEY

    from ui.settings_dialog import SettingsDialog
    from core.refiner import TextRefiner
    import winreg
except Exception as e:
    try:
        app_data_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SFlow")
        os.makedirs(app_data_dir, exist_ok=True)
        with open(os.path.join(app_data_dir, "crash_log.txt"), "w") as f:
            f.write("Import Crash occurred:\n")
            f.write(str(e) + "\n")
            traceback.print_exc(file=f)
    except Exception:
        pass
    sys.exit(1)

def _is_launch_at_login() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, "SFlow")
        winreg.CloseKey(key)
        return True
    except WindowsError:
        return False


# ---------------------------------------------------------------------------
# First-run dialog
# ---------------------------------------------------------------------------
class FirstRunDialog(QDialog):
    """Shown when GROQ_API_KEY is missing on first launch."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SFlow - Setup")
        self.setFixedWidth(420)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Ingresa tu Groq API Key para transcripciones:"))

        link = QLabel('<a href="https://console.groq.com/keys">Obtener gratis en console.groq.com/keys</a>')
        link.setOpenExternalLinks(True)
        layout.addWidget(link)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("gsk_...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_input)

        save_btn = QPushButton("Guardar y continuar")
        save_btn.clicked.connect(self._save_key)
        layout.addWidget(save_btn)

        self.setLayout(layout)

    def _save_key(self):
        key = self.key_input.text().strip()
        if not key.startswith("gsk_") or len(key) < 20:
            QMessageBox.warning(self, "Error", "La clave debe comenzar con 'gsk_' y tener al menos 20 caracteres.")
            return

        env_path = os.path.join(APP_DATA_DIR, ".env")
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        with open(env_path, "w") as f:
            f.write(f"GROQ_API_KEY={key}\n")

        # Set in current process so Transcriber picks it up
        os.environ["GROQ_API_KEY"] = key
        self.accept()


# ---------------------------------------------------------------------------
# Launch at Login
# ---------------------------------------------------------------------------
def _set_launch_at_login(enabled: bool):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        if enabled:
            if getattr(sys, "frozen", False):
                exe = sys.executable
            else:
                exe = os.path.abspath(sys.argv[0])
            winreg.SetValueEx(key, "SFlow", 0, winreg.REG_SZ, f'"{exe}"')
        else:
            try:
                winreg.DeleteValue(key, "SFlow")
            except WindowsError:
                pass
        winreg.CloseKey(key)
    except WindowsError as e:
        print(f"Failed to set launch at login: {e}")


# ---------------------------------------------------------------------------
# System tray
# ---------------------------------------------------------------------------
def _setup_tray(app: QApplication, port: int) -> QSystemTrayIcon:
    pixmap = QPixmap(LOGO_PATH)
    if pixmap.isNull():
        # Fallback: empty icon (shouldn't happen but don't crash)
        icon = QIcon()
    else:
        icon = QIcon(pixmap.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    tray = QSystemTrayIcon(icon, app)

    menu = QMenu()

    status = QAction("SFlow - Activo", menu)
    status.setEnabled(False)
    menu.addAction(status)
    menu.addSeparator()

    settings_action = QAction("Configurar IA...", menu)
    settings_action.triggered.connect(lambda: SettingsDialog().exec())
    menu.addAction(settings_action)
    menu.addSeparator()

    dashboard = QAction(f"Abrir Dashboard (:{port})", menu)
    dashboard.triggered.connect(lambda: subprocess.run(["open", f"http://localhost:{port}"], capture_output=True))
    menu.addAction(dashboard)
    menu.addSeparator()

    login_action = QAction("Iniciar con macOS", menu)
    login_action.setCheckable(True)
    login_action.setChecked(_is_launch_at_login())
    login_action.toggled.connect(_set_launch_at_login)
    menu.addAction(login_action)
    menu.addSeparator()

    quit_action = QAction("Salir", menu)
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)
    tray.setToolTip("SFlow - Voice to Text")
    tray.show()
    return tray


# ---------------------------------------------------------------------------
# Main app controller
# ---------------------------------------------------------------------------
class SFlowApp(QObject):
    """Main application controller. Wires hotkey -> recorder -> transcriber -> clipboard."""

    transcription_done = pyqtSignal(str, float)
    transcription_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber()
        self.refiner = TextRefiner()
        self.db = TranscriptionDB()
        self.hotkey = HotkeyListener()
        self.pill = PillWidget()

        # Connect visualizer to recorder's audio queue
        self.pill.visualizer.set_audio_queue(self.recorder.audio_queue)

        # MUST use QueuedConnection: pynput emits from its own thread
        self.hotkey.pressed.connect(self._on_hotkey_pressed, Qt.ConnectionType.QueuedConnection)
        self.hotkey.released.connect(self._on_hotkey_released, Qt.ConnectionType.QueuedConnection)
        self.transcription_done.connect(self._on_transcription_done, Qt.ConnectionType.QueuedConnection)
        self.transcription_error.connect(self._on_transcription_error, Qt.ConnectionType.QueuedConnection)

    def start(self):
        self.hotkey.start()
        self.pill.show()
        self.pill.set_state(PillWidget.STATE_IDLE)

    @pyqtSlot()
    def _on_hotkey_pressed(self):
        save_frontmost_app()
        self.recorder.start()
        self.pill.set_state(PillWidget.STATE_RECORDING)

    @pyqtSlot()
    def _on_hotkey_released(self):
        duration = self.recorder.stop()
        self.pill.set_state(PillWidget.STATE_PROCESSING)

        if duration < 0.3:
            self.pill.set_state(PillWidget.STATE_IDLE)
            return

        wav_buffer = self.recorder.get_wav_buffer()
        recording_duration = self.recorder.get_duration()
        thread = threading.Thread(
            target=self._transcribe_worker,
            args=(wav_buffer, recording_duration),
            daemon=True,
        )
        thread.start()

    def _transcribe_worker(self, wav_buffer, duration):
        try:
            text = self.transcriber.transcribe(wav_buffer)
            if text:
                text = self.refiner.refine(text)
                self.transcription_done.emit(text, duration)
            else:
                self.transcription_error.emit("No speech detected")
        except Exception as e:
            self.transcription_error.emit(str(e))

    @pyqtSlot(str, float)
    def _on_transcription_done(self, text: str, duration: float):
        paste_text(text)
        self.db.insert(text=text, duration_seconds=duration)
        self.pill.set_state(PillWidget.STATE_DONE)

    @pyqtSlot(str)
    def _on_transcription_error(self, error: str):
        self.pill.set_state(PillWidget.STATE_ERROR)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SFlow")
    app.setQuitOnLastWindowClosed(False)

    # Allow Ctrl+C to kill the app
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # First-run: ask for API key if missing (BEFORE hiding from Dock so dialog is visible)
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        dialog = FirstRunDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

    # Start web dashboard
    port = start_web_server()

    # Start the app
    sflow = SFlowApp()
    sflow.start()

    # System tray icon
    tray = _setup_tray(app, port)  # noqa: F841 — must keep reference alive

    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        try:
            import os
            app_data_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SFlow")
            os.makedirs(app_data_dir, exist_ok=True)
            with open(os.path.join(app_data_dir, "crash_log.txt"), "w") as f:
                f.write(f"Crash occurred:\n")
                f.write(str(e) + "\n")
                traceback.print_exc(file=f)
        except Exception:
            pass
        sys.exit(1)
