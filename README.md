# 📚 MoodleBot

> Automated collection of assignment deadlines and submission statuses from UFSC's Moodle platform, built with Python and Selenium.

Designed to eliminate the need to manually browse each course page to track pending work — MoodleBot logs in, scans every subject in the current semester, and presents all upcoming deadlines in a single sorted table.

---

## Features

- Automated login on [presencial.moodle.ufsc.br](https://presencial.moodle.ufsc.br)
- Automatic discovery of enrolled subjects for the current semester
- Extraction of activities containing a due date (`Vencimento:` keyword)
- Date filter — upcoming only, or all activities including overdue ones
- Detection and selection of multiple curriculum numbers (dual enrolments)
- Per-activity submission status retrieval
- Results table sorted by due date with colour-coded urgency
- CSV export of the full results table
- Per-user personal notes, persisted locally
- Credentials saved locally with **Fernet** symmetric encryption
- Dark UI themed around Moodle's orange brand colour
- Dark title bar on Windows 10 (build 19041+) and Windows 11 via DWM API

---

## Tech Stack

| Library | Role |
|---|---|
| `selenium` | Chrome browser automation |
| `webdriver-manager` | Automatic ChromeDriver download and version management |
| `tkinter` / `ttk` | Desktop GUI |
| `cryptography.fernet` | Symmetric encryption for saved credentials |
| `re` | Regex-based due date extraction from activity descriptions |
| `csv` | Results export |
| `logging` | Structured runtime logs (DEBUG / INFO / WARNING) |
| `threading` | Background scraping thread — keeps the UI responsive |
| `ctypes` | Windows DWM API call for the dark title bar |
| `pathlib` | Cross-platform file path handling |

---

## Project Structure

```
MoodleBot/
├── main.py             # Entry point — instantiates and starts the App
├── app_interface.py    # GUI layer (Tkinter) and application flow control
├── web_functions.py    # Web scraping logic (Selenium)
├── build.py            # PyInstaller packaging script
└── assets/
    └── iconeApp.ico    # Application icon
```

### File responsibilities

**`app_interface.py`** — owns the entire visual and control layer. Defines the design token palette, reusable styled widgets, all application screens (login, scraping progress, results table, notes, FAQ), progress bar, CSV export, and thread orchestration.

**`web_functions.py`** — owns all browser automation. Login flow, multi-curriculum handling, subject discovery, activity extraction, submission status retrieval, and due date parsing via regex.

**`build.py`** — produces the distributable `.exe` via PyInstaller with all necessary hidden imports, a portable `os.pathsep` separator in `--add-data`, and a post-build size report.

---

## Getting Started

**Prerequisites**
- Python 3.10+
- Google Chrome installed

**Install dependencies**
```bash
pip install selenium webdriver-manager cryptography pyinstaller
```

**Run in development**
```bash
python main.py
```

`webdriver-manager` downloads and manages the correct ChromeDriver version automatically — no manual setup required.

---

## Building the Executable

```bash
python build.py
```

The standalone executable is written to `dist/MoodleBot.exe`.

**PyCharm Run Configuration**

| Field | Value |
|---|---|
| Script path | `<project_root>/build.py` |
| Working directory | `<project_root>` ← required |
| Python interpreter | project venv |

> The working directory **must** point to the project root. PyInstaller resolves
> `main.py` and `assets/` relative to it; an incorrect path will cause the build to fail.

After building, always test the `.exe` from outside the project folder to confirm all assets are correctly bundled.

---

## Credentials & Privacy

Saved credentials are stored at:
```
C:\Users\<user>\Documents\Moodle_Credentials\
├── credentials.txt   # Username + Fernet-encrypted password
└── key.key           # Encryption key — never share this file
```

The password is never stored in plain text. To remove saved credentials, use the **"Limpar credenciais"** button on the login screen, or delete the folder manually.

> Deleting `credentials.txt` without deleting `key.key` (or vice versa) leaves an
> orphaned file that is harmless but can be cleaned up manually.

---

## Results Table Legend

| Colour | Meaning |
|---|---|
| 🟢 Green | Assignment submitted |
| 🟡 Amber | Assignment pending — due date is in the future |
| 🔴 Red | Assignment overdue, or status could not be retrieved |

---

## Known Limitations

- The scraper depends on the current HTML structure of Moodle UFSC. Changes to the platform layout may require updates to the CSS selectors in `web_functions.py`.
- The dark title bar feature requires **Windows 10 (build 19041+)** or **Windows 11**. On other platforms the window opens normally with no errors.
- Results are only as complete as Moodle's own data: activities without a `Vencimento:` field in their description are not collected.

---

## Project Goals

- Streamline the daily review of academic pending work
- Practice browser automation, web scraping, and desktop GUI development in a real-world project
- Explore the integration of Selenium, Fernet encryption, Tkinter, and PyInstaller in a single cohesive codebase

---

*© JpeBecker — All rights reserved.*