import web_functions as functions
import sys, os
import csv
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from datetime import datetime
from tkinter import messagebox
from selenium import webdriver
from cryptography.fernet import Fernet
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ─────────────────────────────────────────────────────────────────────────────
# Dark title bar — Windows 10 (build 19041+) and Windows 11
# ─────────────────────────────────────────────────────────────────────────────
import ctypes

def set_dark_titlebar(window):
    """
    Enable the immersive dark title bar on Windows via the Desktop Window
    Manager (DWM) API.  Falls back silently on Linux, macOS, or older
    Windows builds where the API is unavailable.
    """
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1)
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 11 / recent Windows 10)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
        )
        if result != 0:
            # Fallback: attribute 19 (Windows 10 builds 19041-19042)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 19, ctypes.byref(value), ctypes.sizeof(value)
            )
    except Exception:
        pass  # No-op on non-Windows platforms

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Design tokens — single source of truth for the entire UI
# ─────────────────────────────────────────────────────────────────────────────
T = {
    # Moodle-inspired palette: dark charcoal background + orange accent
    "bg":           "#1A1A1A",   # Primary background (soft near-black)
    "bg2":          "#242424",   # Secondary background: cards, panels, navbar
    "bg3":          "#2E2E2E",   # Widget background: Entry, Text, Scrollbar
    "accent":       "#F47B20",   # Moodle orange — primary button, highlights
    "accent_hover": "#FF9340",   # Lighter orange for hover states
    "success":      "#4CAF82",   # Mint green — submitted activity
    "warning":      "#F4A820",   # Amber — pending activity
    "danger":       "#E05252",   # Soft red — overdue / error
    "text":         "#F0EDE8",   # Warm white (avoids harsh contrast with bg)
    "text_dim":     "#8A8580",   # Warm grey — labels, placeholders, footer
    "border":       "#3A3A3A",   # Subtle border colour
    # Typography
    "font_title":   ("Segoe UI", 16, "bold"),
    "font_subtitle":("Segoe UI", 10),
    "font_label":   ("Segoe UI", 10),
    "font_entry":   ("Segoe UI", 11),
    "font_btn":     ("Segoe UI", 10, "bold"),
    "font_small":   ("Segoe UI", 8),
    "font_table":   ("Segoe UI", 10),
    # Table row colours — dark tints that complement the background
    "row_enviado":  "#1A2E22",   # Dark green tint — submitted
    "row_pendente": "#2E2210",   # Dark amber tint — pending
    "row_atrasado": "#2E1414",   # Dark red tint — overdue
}

# ─────────────────────────────────────────────────────────────────────────────
# Credentials storage
# ─────────────────────────────────────────────────────────────────────────────
CREDENTIALS_DIR  = Path.home() / "Documents" / "Moodle_Credentials"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.txt"
KEY_FILE         = CREDENTIALS_DIR / "key.key"
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)


def get_or_create_key() -> Fernet:
    """
    Load the existing Fernet encryption key from disk, or generate and
    persist a new one if none is found.  Isolating this logic prevents the
    key from living as a module-level side-effect and makes it testable.
    """
    if KEY_FILE.exists():
        with open(KEY_FILE, "rb") as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    return Fernet(key)


fernet = get_or_create_key()


# ─────────────────────────────────────────────────────────────────────────────
# Reusable widget helpers
# ─────────────────────────────────────────────────────────────────────────────
def _styled_button(parent, text, command, primary=True, width=None):
    """
    Create a flat, themed tk.Button with hover colour feedback.

    Args:
        parent:  Parent widget.
        text:    Button label.
        command: Callback executed on click.
        primary: True for the orange accent style; False for the muted
                 secondary style.
        width:   Optional fixed character width.

    Returns:
        The configured tk.Button instance (not yet packed/gridded).
    """
    bg     = T["accent"]       if primary else T["bg3"]
    bg_hov = T["accent_hover"] if primary else T["border"]
    fg     = "#FFFFFF"         if primary else T["text"]
    kw = dict(
        text=text, command=command,
        bg=bg, fg=fg, activebackground=bg_hov, activeforeground=fg,
        font=T["font_btn"], bd=0, relief=tk.FLAT,
        padx=14, pady=7, cursor="hand2",
    )
    if width:
        kw["width"] = width
    btn = tk.Button(parent, **kw)
    btn.bind("<Enter>", lambda e: btn.config(bg=bg_hov))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def _styled_entry(parent, show=None, width=28):
    """
    Create a flat, themed tk.Entry with accent-coloured focus highlight.

    Args:
        parent: Parent widget.
        show:   Character mask (e.g. ``"*"`` for password fields).
        width:  Entry width in characters.

    Returns:
        The configured tk.Entry instance (not yet packed/gridded).
    """
    return tk.Entry(
        parent, show=show, width=width,
        bg=T["bg3"], fg=T["text"], insertbackground=T["text"],
        relief=tk.FLAT, bd=0, font=T["font_entry"],
        highlightthickness=1, highlightbackground=T["border"],
        highlightcolor=T["accent"],
    )


def _styled_check(parent, text, variable):
    """
    Create a themed tk.Checkbutton consistent with the dark colour scheme.

    Args:
        parent:   Parent widget.
        text:     Label displayed next to the checkbox.
        variable: tk.BooleanVar bound to this checkbutton.

    Returns:
        The configured tk.Checkbutton instance (not yet packed/gridded).
    """
    return tk.Checkbutton(
        parent, text=text, variable=variable,
        bg=T["bg"], fg=T["text_dim"], selectcolor=T["bg3"],
        activebackground=T["bg"], activeforeground=T["text"],
        font=T["font_label"], bd=0, cursor="hand2",
    )


def _separator(parent, pady=(0, 0)):
    """
    Render a 1 px horizontal rule using the border colour token.

    Args:
        parent: Parent widget.
        pady:   Vertical padding tuple applied to the frame.

    Returns:
        The tk.Frame acting as the separator line.
    """
    f = tk.Frame(parent, bg=T["border"], height=1)
    f.pack(fill=tk.X, padx=20, pady=pady)
    return f


def _apply_ttk_style():
    """
    Apply the custom dark theme to all ttk widgets used by the application
    (Notebook, Treeview, Scrollbar, Progressbar).  Must be called once
    before any ttk widget is instantiated.
    """
    style = ttk.Style()
    style.theme_use("clam")

    # Notebook tabs
    style.configure(
        "TNotebook",
        background=T["bg"], borderwidth=0, tabmargins=0,
    )
    style.configure(
        "TNotebook.Tab",
        background=T["bg2"], foreground=T["text_dim"],
        font=T["font_label"], padding=(16, 6), borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", T["bg"]), ("active", T["bg3"])],
        foreground=[("selected", T["accent"]), ("active", T["text"])],
    )

    # Results Treeview
    style.configure(
        "Moodle.Treeview",
        background=T["bg2"], foreground=T["text"],
        fieldbackground=T["bg2"], rowheight=28,
        font=T["font_table"], borderwidth=0,
    )
    style.configure(
        "Moodle.Treeview.Heading",
        background=T["bg3"], foreground=T["accent"],
        font=("Segoe UI", 10, "bold"), relief=tk.FLAT, borderwidth=0,
    )
    style.map(
        "Moodle.Treeview",
        background=[("selected", T["accent"])],
        foreground=[("selected", "#FFFFFF")],
    )

    # Scrollbar
    style.configure(
        "Moodle.Vertical.TScrollbar",
        background=T["bg3"], troughcolor=T["bg2"],
        borderwidth=0, arrowsize=12,
    )

    # Progress bar
    style.configure(
        "Moodle.Horizontal.TProgressbar",
        troughcolor=T["bg3"], background=T["accent"],
        borderwidth=0, thickness=6,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main application class
# ─────────────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    """
    Root Tkinter window for MoodleBot.

    Manages the full application lifecycle: login screen, scraping progress
    screen, results table, notes tab, and help/FAQ screens.  All browser
    automation is delegated to :mod:`web_functions` and executed on a
    background daemon thread to keep the UI responsive.
    """

    def __init__(self):
        super().__init__()
        self.resizable(False, False)
        self.configure(bg=T["bg"])
        _apply_ttk_style()

        # UI state references
        self.user_entry           = None
        self.username             = None
        self.pass_entry           = None
        self.main_title           = None
        self.description          = None
        self.save_credentials_var = None
        self.all_time_var         = None
        self.show_browser_var     = None
        self.main_browser         = None
        self.table                = None
        self.all_activities       = []
        self.clear_btn            = None
        self.notes_text           = None
        self.status_bar           = None   # Inline status label on the login screen
        self.progress_bar         = None
        self.counter_label        = None
        self._total_subjects      = 0
        self._done_subjects       = 0

        icon_path = get_icon_path("assets/iconeApp.ico")
        try:
            self.iconbitmap(icon_path)
        except Exception:
            pass  # Missing icon does not prevent the application from starting

        self.create_main_ui()
        self.after(10, lambda: set_dark_titlebar(self))

    # ── Login screen ──────────────────────────────────────────────────────────
    def create_main_ui(self):
        """Build and display the login screen, clearing any existing widgets."""
        for widget in self.winfo_children():
            widget.destroy()
        self.all_activities = []

        self.title("Moodle Activity Bot")
        self.geometry("360x480")
        self.configure(bg=T["bg"])

        # Header
        header = tk.Frame(self, bg=T["bg"])
        header.pack(fill=tk.X, padx=30, pady=(28, 6))
        tk.Label(header, text="📚 MoodleBot", font=T["font_title"],
                 bg=T["bg"], fg=T["accent"]).pack(anchor="w")
        tk.Label(header, text="Automação de atividades da UFSC",
                 font=T["font_subtitle"], bg=T["bg"], fg=T["text_dim"]).pack(anchor="w")

        _separator(self, pady=(6, 16))

        # Credentials form
        form = tk.Frame(self, bg=T["bg"])
        form.pack(fill=tk.X, padx=30)

        tk.Label(form, text="Usuário", font=T["font_label"],
                 bg=T["bg"], fg=T["text_dim"]).pack(anchor="w")
        self.user_entry = _styled_entry(form)
        self.user_entry.pack(fill=tk.X, ipady=6, pady=(2, 10))

        tk.Label(form, text="Senha", font=T["font_label"],
                 bg=T["bg"], fg=T["text_dim"]).pack(anchor="w")

        # Password row with show/hide toggle
        pass_row = tk.Frame(form, bg=T["bg"])
        pass_row.pack(fill=tk.X, pady=(2, 10))
        self.pass_entry = _styled_entry(pass_row, show="*")
        self.pass_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, ipady=6)
        self._pass_visible = False
        eye_btn = tk.Button(
            pass_row, text="👁", bg=T["bg3"], fg=T["text_dim"],
            bd=0, relief=tk.FLAT, cursor="hand2", font=("Segoe UI", 11),
            activebackground=T["bg3"], activeforeground=T["text"],
            command=self._toggle_password,
        )
        eye_btn.pack(side=tk.LEFT, padx=(4, 0))
        self._eye_btn = eye_btn

        # Options
        opts = tk.Frame(self, bg=T["bg"])
        opts.pack(fill=tk.X, padx=30)
        self.save_credentials_var = tk.BooleanVar()
        self.all_time_var         = tk.BooleanVar()
        self.show_browser_var     = tk.BooleanVar()
        _styled_check(opts, "Salvar credenciais",       self.save_credentials_var).pack(anchor="w")
        _styled_check(opts, "Mostrar tarefas vencidas", self.all_time_var).pack(anchor="w")
        _styled_check(opts, "Mostrar execução",         self.show_browser_var).pack(anchor="w")

        # Placeholder frame for the "clear credentials" button (populated by load_credentials)
        self.cred_frame = tk.Frame(self, bg=T["bg"])
        self.cred_frame.pack(fill=tk.X, padx=30, pady=(4, 0))
        self.clear_btn = None

        _separator(self, pady=(16, 14))

        btn_row = tk.Frame(self, bg=T["bg"])
        btn_row.pack(fill=tk.X, padx=30)
        _styled_button(btn_row, "Entrar", self.check_login).pack(fill=tk.X, ipady=2)

        # Inline status label (replaces modal messageboxes for transient feedback)
        self.status_bar = tk.Label(
            self, text="", font=T["font_small"],
            bg=T["bg"], fg=T["text_dim"],
        )
        self.status_bar.pack(pady=(8, 0))

        tk.Frame(self, bg=T["bg"]).pack(expand=True)  # Vertical spacer
        self._build_footer(self)

        # Help button (top-right corner)
        tk.Button(
            self, text="?", bg=T["bg2"], fg=T["text_dim"],
            bd=0, relief=tk.FLAT, font=T["font_small"],
            cursor="hand2", activebackground=T["bg2"],
            command=self.show_faq_screen,
        ).place(relx=1.0, rely=0.0, x=-10, y=8, anchor="ne")

        self.load_credentials()

    def _toggle_password(self):
        """Toggle password field visibility between masked and plain text."""
        self._pass_visible = not self._pass_visible
        self.pass_entry.config(show="" if self._pass_visible else "*")
        self._eye_btn.config(fg=T["accent"] if self._pass_visible else T["text_dim"])

    def _set_status(self, msg: str, color: str = None):
        """
        Update the inline status label on the login screen from any thread.

        Args:
            msg:   Text to display.
            color: Hex colour for the label; defaults to ``T["text_dim"]``.
        """
        def _do():
            if self.status_bar:
                self.status_bar.config(text=msg, fg=color or T["text_dim"])
        self.after(0, _do)

    # ── Login logic ───────────────────────────────────────────────────────────
    def check_login(self):
        """
        Validate the form, optionally persist credentials, then launch the
        login background thread.  Shows inline status feedback on errors.
        """
        user     = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        if not user or not password:
            self._set_status("⚠  Preencha usuário e senha.", T["warning"])
            return

        self.username = user
        self.user_entry.config(state="disabled")
        self.pass_entry.config(state="disabled")
        self._set_status("Conectando...", T["accent"])

        if self.save_credentials_var.get():
            try:
                encrypted_password = fernet.encrypt(password.encode())
                cred_is_new = not CREDENTIALS_FILE.exists()
                with open(CREDENTIALS_FILE, "w") as f:
                    f.write(user + "\n")
                    f.write(encrypted_password.decode())
                if cred_is_new:
                    self._set_status("✔  Credenciais salvas.", T["success"])
            except Exception as e:
                self._set_status(f"Erro ao salvar credenciais: {e}", T["danger"])

        threading.Thread(target=self.run_login, args=(user, password), daemon=True).start()

    def run_login(self, user: str, password: str):
        """
        Background thread: initialise the browser, authenticate with Moodle,
        and route the result to the appropriate UI handler.

        Args:
            user:     Plain-text username.
            password: Plain-text password.
        """
        self.after(0, self.show_logged_screen)
        self.main_browser = create_browser(self.show_browser_var.get())
        result = functions.login_moodle(
            active_browser=self.main_browser, user=user, secret=password
        )

        if result["status"] == "success":
            subjects_list = result["data"]
            logger.info("Disciplinas coletadas: %s", subjects_list)
            self._total_subjects = len(subjects_list)
            self._done_subjects  = 0
            self.after(0, lambda: self._init_progress(self._total_subjects))
            threading.Thread(target=self.loop_subject, args=(subjects_list,), daemon=True).start()

        elif result["status"] == "multiple_ids":
            users_ids, links_ids = [], []
            for entry in result["data"]:
                users_ids.append(entry[0])
                links_ids.append(entry[1])
            self.after(0, lambda: self.show_curriculum_opt(users_ids, links_ids))

        else:
            logger.warning("Falha no login: %s", result["status"])
            self._set_status("✖  Credenciais inválidas.", T["danger"])
            self.after(500, self.create_main_ui)
            self.after(600, self.main_browser.quit)

    # ── Results screen ────────────────────────────────────────────────────────
    def show_logged_screen(self):
        """
        Replace the login screen with the scraping progress screen,
        including the results Treeview, progress bar, and notes tab.
        """
        for widget in self.winfo_children():
            widget.destroy()

        self.title("Moodle Activity Bot — Varredura em andamento")
        self.geometry("1020x600")
        self.resizable(True, True)
        self.configure(bg=T["bg"])
        self.after(10, lambda: set_dark_titlebar(self))

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        # ── Activities tab
        act_frame = tk.Frame(notebook, bg=T["bg"])

        top = tk.Frame(act_frame, bg=T["bg"])
        top.pack(fill=tk.X, padx=16, pady=(14, 6))

        left_top = tk.Frame(top, bg=T["bg"])
        left_top.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.main_title = tk.Label(
            left_top, text="🔍  Varredura em andamento…",
            font=T["font_title"], bg=T["bg"], fg=T["accent"],
        )
        self.main_title.pack(anchor="w")
        self.description = tk.Label(
            left_top,
            text="Aguarde enquanto o bot coleta as atividades.",
            font=T["font_subtitle"], bg=T["bg"], fg=T["text_dim"],
        )
        self.description.pack(anchor="w", pady=(2, 0))

        # Activity counter and CSV export button (top-right)
        right_top = tk.Frame(top, bg=T["bg"])
        right_top.pack(side=tk.RIGHT)
        self.counter_label = tk.Label(
            right_top, text="0 atividades", font=T["font_subtitle"],
            bg=T["bg"], fg=T["text_dim"],
        )
        self.counter_label.pack(anchor="e")
        self._export_btn = _styled_button(
            right_top, "⬇  Exportar CSV", self._export_csv, primary=False,
        )
        self._export_btn.pack(anchor="e", pady=(6, 0))
        self._export_btn.config(state=tk.DISABLED)  # Enabled when scraping completes

        # Progress bar
        prog_frame = tk.Frame(act_frame, bg=T["bg"])
        prog_frame.pack(fill=tk.X, padx=16, pady=(0, 8))
        self._prog_label = tk.Label(
            prog_frame, text="Iniciando…",
            font=T["font_small"], bg=T["bg"], fg=T["text_dim"],
        )
        self._prog_label.pack(anchor="w")
        self.progress_bar = ttk.Progressbar(
            prog_frame, style="Moodle.Horizontal.TProgressbar",
            orient=tk.HORIZONTAL, mode="determinate",
        )
        self.progress_bar.pack(fill=tk.X, pady=(2, 0))

        # Results table
        table_frame = tk.Frame(act_frame, bg=T["bg"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 10))

        self.table = ttk.Treeview(
            table_frame,
            style="Moodle.Treeview",
            columns=("Disciplina", "Tarefa", "Prazo", "Status"),
            show="headings",
        )
        col_cfg = {
            "Disciplina": (220, tk.W),
            "Tarefa":     (340, tk.W),
            "Prazo":      (100, tk.CENTER),
            "Status":     (200, tk.CENTER),
        }
        for col, (w, anchor) in col_cfg.items():
            self.table.heading(col, text=col)
            self.table.column(col, width=w, anchor=anchor, stretch=(col == "Tarefa"))

        self.table.tag_configure("enviado",  background=T["row_enviado"],  foreground=T["success"])
        self.table.tag_configure("pendente", background=T["row_pendente"], foreground=T["warning"])
        self.table.tag_configure("atrasado", background=T["row_atrasado"], foreground=T["danger"])

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL,
                            style="Moodle.Vertical.TScrollbar",
                            command=self.table.yview)
        self.table.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.table.pack(fill=tk.BOTH, expand=True)

        # Colour legend
        legend = tk.Frame(act_frame, bg=T["bg"])
        legend.pack(fill=tk.X, padx=16, pady=(0, 6))
        for colour, label in [
            (T["success"], "Enviado"),
            (T["warning"], "Pendente"),
            (T["danger"],  "Atrasado / Erro"),
        ]:
            tk.Label(legend, text=f"● {label}", font=T["font_small"],
                     bg=T["bg"], fg=colour).pack(side=tk.LEFT, padx=(0, 16))

        notebook.add(act_frame, text="  Atividades  ")

        # ── Notes tab
        notes_frame = tk.Frame(notebook, bg=T["bg"])
        tk.Label(notes_frame, text="Anotações Pessoais",
                 font=T["font_title"], bg=T["bg"], fg=T["accent"]).pack(
            anchor="w", padx=16, pady=(14, 4))
        _separator(notes_frame, pady=(0, 8))
        self.notes_text = tk.Text(
            notes_frame, wrap="word",
            bg=T["bg3"], fg=T["text"], insertbackground=T["text"],
            relief=tk.FLAT, bd=0, font=("Segoe UI", 10),
            padx=12, pady=12,
            highlightthickness=1, highlightbackground=T["border"],
        )
        self.notes_text.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))
        self.load_notes()
        _styled_button(notes_frame, "💾  Salvar Anotações", self.save_notes).pack(
            anchor="e", padx=16, pady=(0, 12))
        notebook.add(notes_frame, text="  Anotações  ")

        self._build_footer(self)

    def _init_progress(self, total: int):
        """
        Initialise the progress bar with the total number of subjects.

        Args:
            total: Number of subjects to be scraped.
        """
        if self.progress_bar:
            self.progress_bar.config(maximum=max(total, 1), value=0)
        if self._prog_label:
            self._prog_label.config(text=f"0 / {total} disciplinas")

    def _step_progress(self, done: int, total: int, subject_name: str):
        """
        Advance the progress bar by one step and update the subject label.

        Args:
            done:         Number of subjects processed so far.
            total:        Total number of subjects.
            subject_name: Name of the subject currently being processed.
        """
        if self.progress_bar:
            self.progress_bar.config(value=done)
        if self._prog_label:
            self._prog_label.config(text=f"{done} / {total} — {subject_name}")

    def _update_counter(self):
        """Refresh the activity counter label with the current total."""
        n = len(self.all_activities)
        if self.counter_label:
            self.counter_label.config(text=f"{n} atividade{'s' if n != 1 else ''}")

    # ── CSV export ────────────────────────────────────────────────────────────
    def _export_csv(self):
        """
        Prompt the user for a save path and write all collected activities
        to a UTF-8 CSV file, sorted by due date.
        """
        if not self.all_activities:
            messagebox.showinfo("Exportar", "Nenhuma atividade para exportar.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
            initialfile=f"moodle_atividades_{datetime.today().strftime('%Y%m%d')}.csv",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["Disciplina", "Tarefa", "Prazo", "Status"])
                writer.writeheader()
                writer.writerows(
                    sorted(self.all_activities,
                           key=lambda x: datetime.strptime(x["Prazo"], "%d/%m/%Y"))
                )
            messagebox.showinfo("Exportado", f"Arquivo salvo em:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar: {e}")

    # ── Multiple curriculum selection ─────────────────────────────────────────
    def show_curriculum_opt(self, user_ids: list, links: list):
        """
        Display a modal Toplevel window listing all available curriculum
        numbers so the user can choose which Moodle account to access.

        Args:
            user_ids: List of curriculum ID strings.
            links:    Corresponding list of Moodle URLs for each ID.
        """
        window = tk.Toplevel(self)
        window.title("Selecione a matrícula")
        window.configure(bg=T["bg"])
        window.resizable(False, False)
        window.grab_set()
        window.after(10, lambda: set_dark_titlebar(window))

        tk.Label(window, text="Selecione a matrícula",
                 font=T["font_title"], bg=T["bg"], fg=T["accent"]).pack(pady=(20, 4), padx=30)
        tk.Label(window, text="Você possui mais de um vínculo ativo.",
                 font=T["font_subtitle"], bg=T["bg"], fg=T["text_dim"]).pack(pady=(0, 16), padx=30)
        for uid, link in zip(user_ids, links):
            _styled_button(window, uid,
                           command=lambda l=link: self.select_identity(l, window),
                           primary=False).pack(fill=tk.X, padx=30, pady=4)
        tk.Frame(window, bg=T["bg"], height=16).pack()

    def select_identity(self, user_link: str, window: tk.Toplevel):
        """
        Close the curriculum selection dialog and start the identity
        selection on a background thread.

        Args:
            user_link: Moodle URL for the chosen curriculum.
            window:    The Toplevel dialog to close.
        """
        window.destroy()
        threading.Thread(target=self._run_select_identity, args=(user_link,), daemon=True).start()

    def _run_select_identity(self, user_page: str):
        """
        Background thread: delegate curriculum selection to :mod:`web_functions`
        and begin the subject scraping loop on success.

        Args:
            user_page: Moodle URL for the chosen curriculum.
        """
        try:
            functions.select_curriculum_number(
                active_browser=self.main_browser, user_id_page=user_page)
            subjects = functions.get_subjects(self.main_browser)
            self._total_subjects = len(subjects)
            self._done_subjects  = 0
            self.after(0, lambda: self._init_progress(self._total_subjects))
            threading.Thread(target=self.loop_subject, args=(subjects,), daemon=True).start()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erro", f"Erro ao selecionar identidade: {e}"))
            self.after(0, self.create_main_ui)

    # ── Scraping loop ─────────────────────────────────────────────────────────
    def loop_subject(self, subjects_list: list):
        """
        Background thread: iterate over all subjects, collect activities,
        retrieve submission statuses, and post each result to the UI thread.

        Args:
            subjects_list: List of ``(name, url)`` tuples returned by
                           :func:`web_functions.get_subjects`.
        """
        total = len(subjects_list)
        for idx, subject in enumerate(subjects_list, start=1):
            subject_name = subject[0]
            subject_url  = subject[1]
            logger.info("Percorrendo: %s", subject_name)
            self.after(0, lambda n=subject_name, i=idx: self._step_progress(i, total, n))

            subject_activities = functions.get_activities(
                active_browser=self.main_browser, subject_url=subject_url
            )
            if subject_activities is not None:
                selected = functions.loop_activities(
                    activities_list=subject_activities, all_time=self.all_time_var.get()
                )
                for activity in selected:
                    activity_status = functions.get_activities_status(
                        active_browser=self.main_browser, activity_url=activity[1]
                    )
                    task = {
                        "Disciplina": subject_name,
                        "Tarefa":     activity[0],
                        "Prazo":      activity[2].strftime("%d/%m/%Y"),
                        "Status":     activity_status,
                    }
                    self.after(0, lambda t=task: self.update_results(t))
            else:
                logger.warning("%s: nenhum bloco encontrado.", subject_name)

        self.after(0, self.has_ended_ui)

    def update_results(self, activity: dict):
        """
        Append a newly collected activity to the internal list and insert
        it into the Treeview in date-sorted order.

        Args:
            activity: Dict with keys ``Disciplina``, ``Tarefa``, ``Prazo``,
                      and ``Status``.
        """
        logger.info("Nova atividade: %s | %s", activity["Disciplina"], activity["Tarefa"])
        self.all_activities.append(activity)
        self._insert_sorted(activity)
        self._update_counter()

    def _insert_sorted(self, activity: dict):
        """
        Insert a single activity row into the Treeview at the correct
        chronological position without rebuilding the entire table.

        Args:
            activity: Dict with keys ``Disciplina``, ``Tarefa``, ``Prazo``,
                      and ``Status``.
        """
        new_date = datetime.strptime(activity["Prazo"], "%d/%m/%Y")
        tag = self._resolve_tag(activity["Status"], new_date)
        rows = self.table.get_children()
        insert_index = len(rows)
        for i, row_id in enumerate(rows):
            row_date = datetime.strptime(self.table.set(row_id, "Prazo"), "%d/%m/%Y")
            if new_date < row_date:
                insert_index = i
                break
        self.table.insert(
            "", insert_index,
            values=(activity["Disciplina"], activity["Tarefa"],
                    activity["Prazo"], activity["Status"]),
            tags=(tag,),
        )

    def update_table(self):
        """
        Rebuild the Treeview from scratch using ``self.all_activities``,
        sorted by due date.  Called once at the end of a scraping session
        to guarantee a consistent final sort order.
        """
        for item in self.table.get_children():
            self.table.delete(item)
        for a in sorted(self.all_activities,
                        key=lambda x: datetime.strptime(x["Prazo"], "%d/%m/%Y")):
            prazo = datetime.strptime(a["Prazo"], "%d/%m/%Y")
            self.table.insert(
                "", "end",
                values=(a["Disciplina"], a["Tarefa"], a["Prazo"], a["Status"]),
                tags=(self._resolve_tag(a["Status"], prazo),),
            )

    def _resolve_tag(self, status: str, prazo: datetime) -> str:
        """
        Map a submission status string and due date to a Treeview colour tag.

        Args:
            status: Submission status text from Moodle.
            prazo:  Due date as a datetime object.

        Returns:
            One of ``"enviado"``, ``"pendente"``, or ``"atrasado"``.
        """
        s = status.lower()
        if "nenhum envio" in s or "não enviado" in s:
            return "atrasado" if prazo < datetime.today() else "pendente"
        if "enviado com atraso" in s:
            return "atrasado"
        if "enviado" in s:
            return "enviado"
        return "atrasado"

    def has_ended_ui(self):
        """
        Update the UI to reflect that scraping has completed: set the title,
        update status labels, fill the progress bar, and enable CSV export.
        """
        self.title("Moodle Activity Bot — Concluído")
        self.main_browser.quit()
        self.update_table()

        if self.main_title:
            self.main_title.config(text="✅  Varredura concluída!", fg=T["success"])
        if self.description:
            n = len(self.all_activities)
            self.description.config(
                text=f"{n} atividade{'s' if n != 1 else ''} encontrada{'s' if n != 1 else ''}."
            )
        if self.progress_bar:
            self.progress_bar.config(value=self.progress_bar["maximum"])
        if self._prog_label:
            self._prog_label.config(text="Varredura finalizada.")
        if self._export_btn:
            self._export_btn.config(state=tk.NORMAL)
        self._update_counter()
        logger.info("Varredura concluída. %d atividades.", len(self.all_activities))

    # ── Notes & credentials ───────────────────────────────────────────────────
    def get_notes_file_path(self) -> Path:
        """
        Return the path to the current user's notes file, creating the
        notes directory if it does not yet exist.
        """
        notes_dir = Path.home() / "Documents" / "Moodle_notes"
        notes_dir.mkdir(exist_ok=True)
        return notes_dir / f"{self.username}_notes.txt"

    def save_notes(self):
        """Persist the contents of the notes Text widget to disk."""
        try:
            with open(self.get_notes_file_path(), "w", encoding="utf-8") as f:
                f.write(self.notes_text.get("1.0", tk.END).strip())
            messagebox.showinfo("Anotações", "Anotações salvas com sucesso.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar anotações: {e}")

    def load_notes(self):
        """Populate the notes Text widget from the user's saved notes file."""
        try:
            notes_file = self.get_notes_file_path()
            if notes_file.exists():
                with open(notes_file, "r", encoding="utf-8") as f:
                    self.notes_text.insert("1.0", f.read())
        except Exception as e:
            logger.error("Erro ao carregar anotações: %s", e)

    def load_credentials(self):
        """
        Populate the login form with saved credentials, if available.
        Also renders the "clear credentials" button when a saved file is found.
        """
        try:
            if CREDENTIALS_FILE.exists():
                with open(CREDENTIALS_FILE, "r") as f:
                    user = f.readline().strip()
                    enc  = f.readline().strip().encode()
                    pwd  = fernet.decrypt(enc).decode()
                self.user_entry.insert(0, user)
                self.pass_entry.insert(0, pwd)
                self.save_credentials_var.set(True)
                self.clear_btn = _styled_button(
                    self.cred_frame, "Limpar credenciais",
                    self.clear_credentials, primary=False,
                )
                self.clear_btn.pack(fill=tk.X)
            else:
                logger.info("No saved credentials found.")
        except Exception:
            logger.warning("Could not load saved credentials.")

    def clear_credentials(self):
        """
        Delete the saved credentials and encryption key from disk, then
        reset the form and inline status message.
        """
        try:
            if CREDENTIALS_FILE.exists():
                CREDENTIALS_FILE.unlink()
            if KEY_FILE.exists():
                KEY_FILE.unlink()
            self.user_entry.delete(0, tk.END)
            self.pass_entry.delete(0, tk.END)
            self.save_credentials_var.set(False)
            if self.clear_btn:
                self.clear_btn.destroy()
                self.clear_btn = None
            self._set_status("✔  Credenciais removidas.", T["success"])
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível apagar as credenciais: {e}")

    # ── FAQ screens ───────────────────────────────────────────────────────────
    def show_faq_screen(self):
        """Display the Frequently Asked Questions screen."""
        for widget in self.winfo_children():
            widget.destroy()

        self.title("Ajuda — MoodleBot")
        self.geometry("460x440")
        self.resizable(False, False)
        self.configure(bg=T["bg"])
        self.after(10, lambda: set_dark_titlebar(self))

        tk.Label(self, text="Perguntas Frequentes", font=T["font_title"],
                 bg=T["bg"], fg=T["accent"]).pack(anchor="w", padx=24, pady=(20, 4))
        _separator(self, pady=(0, 14))

        faq_items = [
            ("Onde são salvas as credenciais?",
             "Ao marcar 'Salvar credenciais', elas são gravadas em "
             "Documentos/Moodle_Credentials com criptografia Fernet."),
            ("O que significa 'Mostrar Tarefas Vencidas'?",
             "Inclui na varredura atividades cujo prazo já passou."),
            ("O que 'Mostrar execução' faz?",
             "Abre o Chrome visível durante a coleta de dados."),
            ("Como removo minhas credenciais?",
             "Use o botão 'Limpar credenciais' na tela de login."),
        ]
        for q, a in faq_items:
            blk = tk.Frame(self, bg=T["bg2"], padx=16, pady=10)
            blk.pack(fill=tk.X, padx=24, pady=(0, 8))
            tk.Label(blk, text=q, font=("Segoe UI", 10, "bold"),
                     bg=T["bg2"], fg=T["text"]).pack(anchor="w")
            tk.Label(blk, text=a, font=T["font_subtitle"],
                     bg=T["bg2"], fg=T["text_dim"], wraplength=380, justify="left").pack(anchor="w")

        # Footer and navigation buttons must be packed with side=BOTTOM *before*
        # any top-anchored content to guarantee they remain visible when the
        # window is at its minimum height.
        self._build_footer(self)
        btn_row = tk.Frame(self, bg=T["bg"])
        btn_row.pack(side=tk.BOTTOM, fill=tk.X, padx=24, pady=(0, 12))
        _styled_button(btn_row, "← Voltar ao Login", self.create_main_ui, primary=False).pack(side=tk.LEFT)
        _styled_button(btn_row, "Como funciona?", self.show_bot_info).pack(side=tk.RIGHT)

        tk.Label(self,
                 text="OBS: A coleta está sujeita a erros e não substitui o uso do Moodle pessoal.",
                 font=T["font_small"], bg=T["bg"], fg=T["text_dim"], wraplength=400,
                 ).pack(padx=24, pady=(4, 8), anchor="w")

    def show_bot_info(self):
        """Display the step-by-step explanation of the bot's scraping process."""
        for widget in self.winfo_children():
            widget.destroy()

        self.title("Como funciona — MoodleBot")
        self.geometry("560x520")
        self.resizable(False, False)
        self.configure(bg=T["bg"])
        self.after(10, lambda: set_dark_titlebar(self))

        tk.Label(self, text="Como o bot funciona", font=T["font_title"],
                 bg=T["bg"], fg=T["accent"]).pack(anchor="w", padx=24, pady=(20, 4))
        _separator(self, pady=(0, 14))

        steps = [
            ("1", "Login",         "Acessa sua conta no Moodle da UFSC."),
            ("2", "Disciplinas",   "Captura as URLs das matérias do semestre atual."),
            ("3", "Atividades",    "Percorre cada disciplina coletando os blocos de atividade."),
            ("4", "Filtro de prazo","Verifica a palavra-chave 'Vencimento' na descrição."),
            ("5", "Status",        "Acessa cada atividade e lê o status de envio."),
            ("6", "Resultado",     "Exibe tudo na tabela e permite exportar para CSV."),
        ]
        for num, title, desc in steps:
            row = tk.Frame(self, bg=T["bg"])
            row.pack(fill=tk.X, padx=24, pady=(0, 6))
            tk.Label(row, text=num, font=("Segoe UI", 13, "bold"), width=3,
                     bg=T["accent"], fg="#FFF").pack(side=tk.LEFT, padx=(0, 12), ipady=4)
            blk = tk.Frame(row, bg=T["bg"])
            blk.pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Label(blk, text=title, font=("Segoe UI", 10, "bold"),
                     bg=T["bg"], fg=T["text"]).pack(anchor="w")
            tk.Label(blk, text=desc, font=T["font_subtitle"],
                     bg=T["bg"], fg=T["text_dim"], wraplength=430, justify="left").pack(anchor="w")

        tk.Label(self,
                 text="OBS: A varredura está sujeita a erros e não substitui o uso do Moodle pessoal.",
                 font=T["font_small"], bg=T["bg"], fg=T["text_dim"], wraplength=480,
                 ).pack(padx=24, pady=(12, 0), anchor="w")

        # Same bottom-first packing rule as show_faq_screen
        self._build_footer(self)
        btn_row = tk.Frame(self, bg=T["bg"])
        btn_row.pack(side=tk.BOTTOM, fill=tk.X, padx=24, pady=(0, 12))
        _styled_button(btn_row, "← Voltar ao FAQ", self.show_faq_screen, primary=False).pack(side=tk.LEFT)

    # ── Shared footer ─────────────────────────────────────────────────────────
    @staticmethod
    def _build_footer(parent):
        """
        Append a copyright footer label anchored to the bottom of *parent*.
        Must be called before packing any ``side=tk.TOP`` content that
        should appear above it.

        Args:
            parent: The widget that will host the footer.
        """
        tk.Label(
            parent,
            text=f"© {datetime.today().year} JpeBecker — Todos os direitos reservados.",
            font=T["font_small"], bg=T["bg2"], fg=T["text_dim"],
            anchor="center", pady=6,
        ).pack(side=tk.BOTTOM, fill=tk.X)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level utilities
# ─────────────────────────────────────────────────────────────────────────────
def create_browser(show_browser: bool = False) -> webdriver.Chrome:
    """
    Instantiate a configured Chrome WebDriver instance.

    A single browser is shared across the entire scraping session to
    preserve the authenticated Moodle cookie.

    Args:
        show_browser: When ``True``, Chrome runs in headed mode so the user
                      can observe the automation.  Defaults to headless.

    Returns:
        A ready-to-use ``webdriver.Chrome`` instance.
    """
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")
    if not show_browser:
        options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def get_icon_path(relative_path: str) -> str:
    """
    Resolve an asset path that works both in development and after
    PyInstaller bundles the application into a single executable.

    Args:
        relative_path: Path to the asset relative to the project root.

    Returns:
        Absolute path to the asset, accounting for ``sys._MEIPASS`` when
        running from a PyInstaller bundle.
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)