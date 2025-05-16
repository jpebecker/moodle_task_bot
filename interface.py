import functions  # crawler functions
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from datetime import datetime
from tkinter import messagebox
from cryptography.fernet import Fernet

########################################################Credentials Section
#credentials path
CREDENTIALS_DIR = Path.home() / "Documents" / "Moodle_Credentials"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.txt"
KEY_FILE = CREDENTIALS_DIR / "key.key"

#check if directory path exist
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

#read or write credential
if KEY_FILE.exists():
    with open(KEY_FILE, 'rb') as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(key)

fernet = Fernet(key)

########################################################App interface Class
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Moodle Bot")
        self.geometry("300x250")
        self.resizable(False, False)
        self.clear_btn = None  #botao de limpar credenciais (se for usado)
        self.create_login_ui()

    def create_login_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        tk.Label(self, text="Usuário:", anchor="e", width=12).grid(row=0, column=0, padx=10, pady=10)
        self.user_entry = tk.Entry(self, width=25)
        self.user_entry.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(self, text="Senha:", anchor="e", width=12).grid(row=1, column=0, padx=10, pady=10)
        self.pass_entry = tk.Entry(self, width=25, show="*")
        self.pass_entry.grid(row=1, column=1, padx=10, pady=10)

        self.save_credentials_var = tk.BooleanVar()
        save_checkbox = tk.Checkbutton(self, text="Salvar credenciais", variable=self.save_credentials_var)
        save_checkbox.grid(row=2, column=0, columnspan=2)

        self.all_time_var = tk.BooleanVar()
        all_time_checkbox = tk.Checkbutton(self, text="All Published", variable=self.all_time_var)
        all_time_checkbox.grid(row=3, column=0, columnspan=2)

        login_btn = tk.Button(self, text="Login", width=20, command=self.handle_login)
        login_btn.grid(row=4, column=0, columnspan=2, pady=10)

        self.clear_btn = None  # Inicializa sem o botão
        self.load_credentials()

    def handle_login(self):
        user = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        if not user or not password:
            messagebox.showwarning("Aviso", "Por favor, preencha usuário e senha.")
            return

        self.user_entry.config(state='disabled')
        self.pass_entry.config(state='disabled')

        if self.save_credentials_var.get():
            try:
                encrypted_password = fernet.encrypt(password.encode())
                cred_was_saved = not CREDENTIALS_FILE.exists()  # Verifica se o arquivo já existia

                with open(CREDENTIALS_FILE, 'w') as f:
                    f.write(user + '\n')
                    f.write(encrypted_password.decode())

                if cred_was_saved:
                    messagebox.showinfo("Credenciais salvas", f"Credenciais salvas com sucesso em:\n{CREDENTIALS_FILE}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar credenciais: {e}")

        threading.Thread(target=self.run_login, args=(user, password, self.all_time_var.get()), daemon=True).start()

    def run_login(self, user, password, all_time):
        self.after(0, self.show_logged_screen)
        df = functions.login_moodle(user, password, all_time=all_time)
        if df is not None:
            self.after(0, lambda: self.show_results_screen(df))
        else:
            self.after(0, lambda: messagebox.showerror("Erro", f"Falha nas credenciais\n"))
            self.after(0, self.create_login_ui)

    def load_credentials(self):
        try:
            if CREDENTIALS_FILE.exists():
                with open(CREDENTIALS_FILE, 'r') as f:
                    user = f.readline().strip()
                    encrypted_password = f.readline().strip().encode()
                    password = fernet.decrypt(encrypted_password).decode()

                    self.user_entry.insert(0, user)
                    self.pass_entry.insert(0, password)
                    self.save_credentials_var.set(True)

                #botao de limpar credenciais
                self.clear_btn = tk.Button(self, text="Limpar credenciais salvas", command=self.clear_credentials)
                self.clear_btn.grid(row=5, column=0, columnspan=2)
        except Exception as exc:
            messagebox.showwarning("Erro", f"Erro ao carregar credenciais salvas: {exc}")

    def clear_credentials(self):
        try:
            if CREDENTIALS_FILE.exists():
                CREDENTIALS_FILE.unlink()
            if KEY_FILE.exists():
                KEY_FILE.unlink()
            messagebox.showinfo(
                "Credenciais removidas",
                f"Credenciais apagadas com sucesso de:\n{CREDENTIALS_FILE}"
            )
            self.user_entry.delete(0, tk.END)
            self.pass_entry.delete(0, tk.END)
            self.save_credentials_var.set(False)

            if self.clear_btn:
                self.clear_btn.destroy()
                self.clear_btn = None
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível apagar as credenciais: {e}")

    def show_logged_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.title("Conectado ao Moodle")

        tk.Label(self, text="Login realizado com sucesso!", font=("Arial", 14)).pack(pady=20)
        tk.Label(
            self,
            text="Aguarde o fim da varredura para que esta página atualize automaticamente",
            font=("Arial", 10),
            wraplength=250,
            justify="center"
        ).pack(pady=20)

    def show_results_screen(self, df):
        for widget in self.winfo_children():
            widget.destroy()

        self.title("Tarefas Pendentes")

        altura_px = min(700, max(300, len(df) * 25))
        largura_px = 1000
        self.geometry(f"{largura_px}x{altura_px}")

        frame = tk.Frame(self)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        vsb = tk.Scrollbar(frame, orient="vertical")
        hsb = tk.Scrollbar(frame, orient="horizontal")

        tree = ttk.Treeview(
            frame,
            columns=list(df.columns),
            show='headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        vsb.config(command=tree.yview)
        vsb.pack(side='right', fill='y')
        hsb.config(command=tree.xview)
        hsb.pack(side='bottom', fill='x')
        tree.pack(fill='both', expand=True)

        for col in df.columns:
            tree.heading(col, text=col)
            max_width = max(df[col].astype(str).apply(len).max(), len(col)) * 7
            tree.column(col, width=min(max_width, 400), anchor='w')

        tree.tag_configure('atrasado', background='#f8d7da')
        tree.tag_configure('pendente', background='#fff3cd')
        tree.tag_configure('enviado', background='#d4edda')

        for _, row in df.iterrows():
            status = str(row['Status']).lower()
            prazo = datetime.strptime(row['Prazo'], "%d/%m/%Y").date()

            if 'nenhum envio' in status or 'não enviado' in status:
                if prazo < datetime.today().date():
                    tag = 'atrasado'
                else:
                    tag = 'pendente'
               
            elif 'enviado com atraso' in status:
                tag = 'atrasado'

            elif 'enviado' in status:
                tag = 'enviado'
            else:
                tag = 'atrasado'

            tree.insert('', 'end', values=list(row), tags=(tag,))


if __name__ == '__main__':
    app = App()
    app.mainloop()