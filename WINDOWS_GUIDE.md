# SFlow for Windows 11

Welcome to the Windows 11 version of SFlow! This port features robust native integration with the Windows OS, system tray accessibility, and brand-new AI Refinement capabilities.

## Features

- **System-wide Dictation**: Use SFlow across any Windows application (Word, Chrome, VS Code) utilizing simulated keystrokes.
- **Floating Pill Overlay**: Always-on-top, non-intrusive UI that reacts to your voice without stealing window focus.
- **Two Recording Modes**:
  - _Push-to-Talk_: Hold `Ctrl+Alt` (or whatever modified according to your preference), speak, and release.
  - _Hands-Free_: Double-tap `Ctrl` to start, tap `Ctrl` again to stop.
- **AI Refinement (New ✨)**:
  - Automatically structures chaotic voice transcriptions into logical sequences.
  - Configurable output formats: _Prompt, Correo electrónico, Informe, Novela._
  - Context-awareness via a custom context field.
- **Windows Auto-Start**: Configurable option in the system tray to automatically start SFlow when you log into Windows.
- **Web Dashboard**: Local history dashboard keeping track of all your transcriptions.

## Installation Process

### Option 1: Quick Install (Standalone Executable)

1. Ensure you have Python installed.
2. Double-click the `build.bat` file in your File Explorer, or run it from the command line in the project root:
   ```cmd
   .\build.bat
   ```
   This will automatically install dependencies, download PyInstaller if missing, and compile the app.
3. Once the build finishes, open the newly created `dist\SFlow` folder.
4. Run `SFlow.exe`. The app will sit in your Windows System Tray (near the clock).
5. On the first launch, it will prompt you for your Groq API Key.

### Option 2: Dev Environment

1. Ensure you have Python 3.12+ installed.
2. Open a terminal (Command Prompt or PowerShell) in the `sflow` directory.
3. Create and activate a virtual environment:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install the required Windows dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
5. Run the application:
   ```cmd
   python main.py
   ```

## How to Get and Configure your Groq API Key

For SFlow to perform transcription and AI Refinement, it requires a free API key from Groq.

1. **Get the Key**:
   - Go to [console.groq.com/keys](https://console.groq.com/keys) and create a free account if you don't have one.
   - Click **Create API Key**, give it a name like "SFlow", and copy the generated key.

2. **Configure SFlow**:
   - **First Launch**: When you start SFlow for the first time, an input dialog will pop up asking for your Groq API Key. Simply paste the key there and click OK.
   - **Manual Update**: If you need to change the key later, you can right-click the SFlow icon in the System Tray, look for the API Key setup option if available, or alternatively update your `.env` file manually.

## How to Configure AI Refinement
1. Find the **SFlow icon** in your Windows System Tray.
2. Right-click the icon and select **"Configurar IA..."**.
3. Check **"Activar refinamiento automático"** to enable the feature.
4. Select your desired output **Formato** (e.g., _Prompt_).
5. Add any extra information in the **Campo de contextualización** (e.g., _Desarrollo de CRM en Python_).
6. Click **Guardar**.
7. Start dictating! The messy transcript will be cleaned and reformatted by the LLM before pasting.

## Troubleshooting: Hotkeys (Ctrl+Alt hold / double-tap Ctrl) not working

If the pill doesn't appear and nothing happens when you press the hotkeys, this
is almost always a **privilege mismatch**. Windows (UIPI) silently blocks a
keyboard hook from a lower-privilege process from seeing keystrokes while a
higher-privilege (Run as Administrator) window has focus — no error, no
crash, the keys are just dropped.

**How to confirm:** check `%LOCALAPPDATA%\SFlow\hotkey.log`. If it only shows
`HotkeyListener.start() called` / `keyboard.Listener started` and never logs
any key press/tap events no matter how much you type, the hook isn't
receiving input at all (this rules out a double-tap timing issue).

**Fix:**
1. Close SFlow (right-click tray icon → Quit, or End Task in Task Manager).
2. Relaunch `SFlow.exe` with **Run as administrator** (right-click → Run as
   administrator), so it matches the privilege level of whatever elevated
   windows you use.
3. Try the hotkey again in the app you want to dictate into.

If you don't run any elevated apps/terminals, SFlow doesn't need to be
elevated either — the mismatch only breaks things when the *focused* window
has higher privileges than SFlow.

