# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SFlow — Windows desktop app."""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# --- Collect sounddevice portaudio binary ---
sounddevice_datas = collect_data_files('_sounddevice_data')

# --- Collect setuptools data (fixes setuptools missing Lorem ipsum.txt error) ---
try:
    setuptools_datas = collect_data_files('setuptools')
except Exception:
    setuptools_datas = []

# --- Collect pynput backends ---
pynput_hidden = collect_submodules('pynput')

# --- Data files ---
datas = [
    ('logo_small.png', '.'),
    ('logo.png', '.'),
]
datas += sounddevice_datas
datas += setuptools_datas

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # pynput
        *pynput_hidden,
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        # PyQt6
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        # Flask
        'flask',
        'jinja2',
        'markupsafe',
        'werkzeug',
        # sounddevice
        '_sounddevice',
        'sounddevice',
        '_cffi_backend',
        # groq + httpx
        'groq',
        'httpx',
        'httpcore',
        'h11',
        'anyio',
        'sniffio',
        'certifi',
        'idna',
        # numpy
        'numpy',
        # dotenv
        'dotenv',
        # win32
        'win32gui',
        'win32con',
        'win32process',
        # clipboard
        'pyperclip'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'test',
        'AppKit',
        'objc'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='logo.ico', # Assuming no ico generated right now, let's keep it default if we don't have it
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SFlow',
)
