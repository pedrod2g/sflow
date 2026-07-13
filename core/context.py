"""Detect active app and map to tone profile for LLM cleanup.

Uses NSWorkspace (PyObjC) to get the frontmost app's bundle identifier.
Falls back to AppleScript name if PyObjC unavailable.
"""
import subprocess


# Bundle ID / app name → tone profile
_APP_TO_TONE = {
    # Chat
    "com.tinyspeck.slackmacgap": "chat",
    "com.hnc.Discord": "chat",
    "WhatsApp": "chat",
    "Telegram": "chat",
    "com.apple.MobileSMS": "chat",  # Messages
    "Messages": "chat",

    # Email
    "com.apple.mail": "email",
    "Mail": "email",
    "com.microsoft.Outlook": "email",
    "Outlook": "email",
    "com.google.Gmail": "email",

    # Code
    "com.todesktop.230313mzl4w4u92": "code",  # Cursor
    "Cursor": "code",
    "com.microsoft.VSCode": "code",
    "Code": "code",
    "com.jetbrains.WebStorm": "code",
    "com.jetbrains.intellij": "code",
    "com.jetbrains.pycharm": "code",
    "com.apple.Terminal": "code",
    "Terminal": "code",
    "com.googlecode.iterm2": "code",
    "iTerm2": "code",
    "dev.warp.Warp-Stable": "code",
    "Warp": "code",

    # Notes / Docs
    "com.apple.Notes": "note",
    "Notes": "note",
    "notion.id": "note",
    "Notion": "note",
    "com.apple.TextEdit": "note",
    "TextEdit": "note",
    "md.obsidian": "note",
    "Obsidian": "note",

    # Formal
    "com.microsoft.Word": "formal",
    "Microsoft Word": "formal",
    "com.apple.iWork.Pages": "formal",
    "Pages": "formal",
    "com.google.Chrome": "default",  # too general
}


def _detect_via_workspace() -> tuple[str, str]:
    """Returns (bundle_id, app_name). May return empty strings if detection fails."""
    try:
        from AppKit import NSWorkspace
        ws = NSWorkspace.sharedWorkspace()
        active = ws.frontmostApplication()
        if active is None:
            return "", ""
        bundle = active.bundleIdentifier() or ""
        name = active.localizedName() or ""
        return str(bundle), str(name)
    except Exception:
        return "", ""


def _detect_via_osascript() -> tuple[str, str]:
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of first process whose frontmost is true'],
            capture_output=True, text=True, timeout=1,
        )
        name = result.stdout.strip()
        return "", name
    except Exception:
        return "", ""


def detect_active_app() -> tuple[str, str]:
    bundle, name = _detect_via_workspace()
    if bundle or name:
        return bundle, name
    return _detect_via_osascript()


def tone_for_active_app() -> str:
    bundle, name = detect_active_app()
    # Match by bundle id first (most reliable), then by name
    if bundle and bundle in _APP_TO_TONE:
        return _APP_TO_TONE[bundle]
    if name and name in _APP_TO_TONE:
        return _APP_TO_TONE[name]
    # Partial match on name (e.g. "Slack 4.41")
    for key, tone in _APP_TO_TONE.items():
        if name and key.lower() in name.lower():
            return tone
    return "default"
