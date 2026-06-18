"""
build.py — MoodleBot
====================
Packages the application into a standalone executable using PyInstaller.

Usage (PyCharm):
    1. Open this file.
    2. Run -> Run 'build'  (or press Shift+F10).
    3. The executable is written to dist/MoodleBot.exe.

Requirements:
    pip install pyinstaller webdriver-manager selenium cryptography
"""

import os
import sys
from pathlib import Path
import PyInstaller.__main__

# ─────────────────────────────────────────────────────────────────────────────
# Build configuration
# ─────────────────────────────────────────────────────────────────────────────
MAIN_SCRIPT = "main.py"
APP_NAME    = "MoodleBot"
ICON_PATH   = Path("assets/iconeApp.ico")

# os.pathsep resolves to ";" on Windows and ":" on Linux/macOS automatically,
# ensuring the --add-data argument is portable across operating systems.
ADD_DATA = [
    f"assets{os.pathsep}assets",
]

# Modules that PyInstaller cannot detect through static analysis and must be
# explicitly declared so they are included in the bundle.
HIDDEN_IMPORTS = [
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "selenium",
    "selenium.webdriver.chrome.options",
    "selenium.webdriver.chrome.service",
    "webdriver_manager",
    "webdriver_manager.chrome",
    "cryptography",
    "cryptography.fernet",
    "logging",
    "csv",
    "threading",
]

# ─────────────────────────────────────────────────────────────────────────────
# Argument assembly
# ─────────────────────────────────────────────────────────────────────────────
args = [
    MAIN_SCRIPT,
    "--onefile",        # Bundle everything into a single executable
    "--windowed",       # Suppress the console window (GUI mode)
    f"--name={APP_NAME}",
    "--noconfirm",      # Overwrite previous build output without prompting
    "--clean",          # Clear PyInstaller cache before each build
    "--log-level=WARN", # Reduce build output noise (was DEBUG)
]

for data in ADD_DATA:
    args.append(f"--add-data={data}")

for hi in HIDDEN_IMPORTS:
    args.append(f"--hidden-import={hi}")

# Icon is optional: a missing file emits a warning but does not abort the build.
if ICON_PATH.exists():
    args.append(f"--icon={ICON_PATH}")
else:
    print(f"[WARNING] Icon not found at '{ICON_PATH}' — build will continue without one.")

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print(f"  Starting build: {APP_NAME}")
    print(f"  Python:         {sys.version}")
    print(f"  Platform:       {sys.platform}")
    print("=" * 60)

    PyInstaller.__main__.run(args)

    exe_path = Path("dist") / (APP_NAME + (".exe" if sys.platform == "win32" else ""))
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 60)
        print(f"  Build successful!")
        print(f"  Executable: {exe_path.resolve()}")
        print(f"  Size:       {size_mb:.1f} MB")
        print("=" * 60)
    else:
        print("\nBuild failed — executable not found in dist/")
        sys.exit(1)